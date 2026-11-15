"""Write a Bambu Studio project (.3mf) from build123d shapes.

Bambu's project flavour of 3MF is a zip with the meshes, a JSON of every print setting
and an XML that names the parts and their filaments. Bambu does not document it; the
layout here follows a project saved by Bambu Studio 02.08 and what OrcaSlicer writes.
"""

from __future__ import annotations

import json
import uuid
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from xml.sax.saxutils import quoteattr

MODEL_NS = (
    'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
    'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
    'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p"'
)
IDENTITY_3X4 = "1 0 0 0 1 0 0 0 1 0 0 0"
IDENTITY_4X4 = "1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"


@dataclass
class PartSpec:
    name: str
    shape: object  # a build123d Shape; tessellated as it is, in the object's own coordinates
    extruder: int  # 1-based filament slot


@dataclass
class ObjectSpec:
    name: str
    parts: list[PartSpec]
    position: tuple[float, float]  # where the shapes' origin lands on the bed; z stays 0


def _uuid(*key: object) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "bambu3mf/" + "/".join(map(str, key))))


def _welded(shape, tolerance: float, angular_tolerance: float) -> tuple[list[str], list[tuple[int, int, int]]]:
    """Tessellate and merge coincident vertices.

    OCC tessellates face by face, so the points along a shared edge come out once per face. STL
    readers weld them by position; Bambu Studio's 3MF reader trusts the indices as written and
    reports every unshared edge as an "open edge". Welding by the rounded coordinates we write
    keeps the mesh watertight. Degenerate triangles left by the weld are dropped.
    """
    vertices, triangles = shape.tessellate(tolerance, angular_tolerance)
    keys = [f'x="{v.X:.4f}" y="{v.Y:.4f}" z="{v.Z:.4f}"' for v in vertices]
    index: dict[str, int] = {}
    remap = []
    for key in keys:
        remap.append(index.setdefault(key, len(index)))
    welded = []
    for a, b, c in triangles:
        tri = (remap[a], remap[b], remap[c])
        if len(set(tri)) == 3:
            welded.append(tri)
    return list(index), welded


def _mesh_xml(shape, mesh_id: int, tolerance: float, angular_tolerance: float) -> tuple[str, int]:
    vertices, triangles = _welded(shape, tolerance, angular_tolerance)
    vs = "\n".join(f"     <vertex {key}/>" for key in vertices)
    ts = "\n".join(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in triangles)
    xml = (
        f'  <object id="{mesh_id}" p:UUID="{_uuid("mesh", mesh_id)}" type="model">\n'
        f"   <mesh>\n    <vertices>\n{vs}\n    </vertices>\n    <triangles>\n{ts}\n    </triangles>\n   </mesh>\n  </object>"
    )
    return xml, len(triangles)


def _model_file(resources: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<model unit="millimeter" xml:lang="en-US" {MODEL_NS}>\n'
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
        f" <resources>\n{resources}\n </resources>\n <build/>\n</model>\n"
    )


def apply_print_overrides(settings: dict, overrides: dict[str, str]) -> dict:
    """Return `settings` with process-preset values changed and the changes declared.

    On load, Bambu Studio rebuilds every preset from the system preset the file names and takes
    from the project only the keys listed in `different_settings_to_system` (one entry for the
    process preset, one per filament, one for the printer). A changed value that is not listed
    there is silently replaced by the system value.
    """
    out = dict(settings) | overrides
    slots = len(settings["filament_colour"]) + 2
    diffs = list(settings.get("different_settings_to_system") or [])
    diffs += [""] * (slots - len(diffs))
    listed = [k for k in diffs[0].split(";") if k]
    diffs[0] = ";".join(listed + [k for k in overrides if k not in listed])
    out["different_settings_to_system"] = diffs
    return out


def write_project(
    path: Path,
    settings: dict,
    objects: list[ObjectSpec],
    title: str,
    print_overrides: dict[str, str] | None = None,
    tolerance: float = 0.01,
    angular_tolerance: float = 0.1,
) -> Path:
    """Write `objects` on one plate with `settings` (a Bambu project_settings JSON) to `path`."""
    if print_overrides:
        settings = apply_print_overrides(settings, print_overrides)
    today = date.today().isoformat()
    # Bambu Studio reads project settings, parts and filaments only from files whose Application tag
    # starts with "BambuStudio-" (bbs_3mf.cpp, _handle_end_metadata). Anything else loads as bare geometry.
    application = f"BambuStudio-{settings['version']}"
    files: dict[str, str] = {}
    resources, items, config, rels = [], [], [], []
    next_id = 1
    for n, obj in enumerate(objects, start=1):
        meshes, parts = [], []
        for part in obj.parts:
            xml, faces = _mesh_xml(part.shape, next_id, tolerance, angular_tolerance)
            meshes.append(xml)
            parts.append((next_id, part, faces))
            next_id += 1
        oid = next_id
        next_id += 1
        model_path = f"/3D/Objects/object_{n}.model"
        files[model_path.lstrip("/")] = _model_file("\n".join(meshes))
        rels.append(f' <Relationship Target="{model_path}" Id="rel-{n}" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>')

        comps = "\n".join(
            f'    <component p:path="{model_path}" objectid="{mid}" p:UUID="{_uuid("component", mid)}" transform="{IDENTITY_3X4}"/>'
            for mid, _, _ in parts
        )
        resources.append(f'  <object id="{oid}" p:UUID="{_uuid("object", oid)}" type="model">\n   <components>\n{comps}\n   </components>\n  </object>')
        x, y = obj.position
        items.append(f'  <item objectid="{oid}" p:UUID="{_uuid("item", oid)}" transform="1 0 0 0 1 0 0 0 1 {x:.4f} {y:.4f} 0" printable="1"/>')

        config.append(f'  <object id="{oid}">')
        config.append(f"    <metadata key=\"name\" value={quoteattr(obj.name)}/>")
        config.append(f'    <metadata key="extruder" value="{obj.parts[0].extruder}"/>')
        config.append(f'    <metadata face_count="{sum(f for _, _, f in parts)}"/>')
        for mid, part, faces in parts:
            config.append(f'    <part id="{mid}" subtype="normal_part">')
            config.append(f"      <metadata key=\"name\" value={quoteattr(part.name)}/>")
            config.append(f'      <metadata key="matrix" value="{IDENTITY_4X4}"/>')
            config.append(f'      <metadata key="extruder" value="{part.extruder}"/>')
            config.append(
                f'      <mesh_stat face_count="{faces}" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>'
            )
            config.append("    </part>")
        config.append("  </object>")

    config.append("  <plate>")
    config.append('    <metadata key="plater_id" value="1"/>')
    config.append('    <metadata key="plater_name" value=""/>')
    config.append('    <metadata key="locked" value="false"/>')
    config.append('    <metadata key="filament_map_mode" value="Auto For Flush"/>')
    for n, item in enumerate(items, start=1):
        oid = item.split('objectid="')[1].split('"')[0]
        config.append("    <model_instance>")
        config.append(f'      <metadata key="object_id" value="{oid}"/>')
        config.append('      <metadata key="instance_id" value="0"/>')
        config.append(f'      <metadata key="identify_id" value="{100 + n}"/>')
        config.append("    </model_instance>")
    config.append("  </plate>")

    files["3D/3dmodel.model"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<model unit="millimeter" xml:lang="en-US" {MODEL_NS}>\n'
        f' <metadata name="Application">{application}</metadata>\n'
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
        f' <metadata name="CreationDate">{today}</metadata>\n'
        f' <metadata name="ModificationDate">{today}</metadata>\n'
        f" <metadata name=\"Title\">{title}</metadata>\n"
        " <resources>\n" + "\n".join(resources) + "\n </resources>\n"
        f' <build p:UUID="{_uuid("build")}">\n' + "\n".join(items) + "\n </build>\n</model>\n"
    )
    files["3D/_rels/3dmodel.model.rels"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        + "\n".join(rels)
        + "\n</Relationships>\n"
    )
    files["_rels/.rels"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n'
        "</Relationships>\n"
    )
    files["[Content_Types].xml"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
        "</Types>\n"
    )
    files["Metadata/model_settings.config"] = '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n' + "\n".join(config) + "\n</config>\n"
    files["Metadata/project_settings.config"] = json.dumps(settings, indent=4, ensure_ascii=False) + "\n"
    files["Metadata/slice_info.config"] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n  <header>\n'
        '    <header_item key="X-BBL-Client-Type" value="slicer"/>\n'
        f'    <header_item key="X-BBL-Client-Version" value="{settings.get("version", "")}"/>\n'
        "  </header>\n</config>\n"
    )

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    order = ["[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model", "3D/_rels/3dmodel.model.rels"]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in order + sorted(set(files) - set(order)):
            z.writestr(name, files[name])
    return path
