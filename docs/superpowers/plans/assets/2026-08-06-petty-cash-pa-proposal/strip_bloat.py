"""Removes slideLayouts/printerSettings/thumbnail parts a python-pptx deck
never uses, so the resulting .pptx is smaller to move around."""
import re
import zipfile


def strip(src_path, dst_path):
    z = zipfile.ZipFile(src_path)
    names = z.namelist()
    data = {n: z.read(n) for n in names}
    z.close()

    used_layouts = set()
    for n in names:
        m = re.match(r"ppt/slides/_rels/(slide\d+)\.xml\.rels", n)
        if m:
            content = data[n].decode("utf-8")
            used_layouts.update(
                re.findall(r'Target="\.\./slideLayouts/(slideLayout\d+\.xml)"', content)
            )

    all_layouts = {
        re.match(r"ppt/slideLayouts/(slideLayout\d+\.xml)$", n).group(1)
        for n in names
        if re.match(r"ppt/slideLayouts/(slideLayout\d+\.xml)$", n)
    }
    unused_layouts = all_layouts - used_layouts

    remove_files = set()
    for lay in unused_layouts:
        remove_files.add(f"ppt/slideLayouts/{lay}")
        remove_files.add(f"ppt/slideLayouts/_rels/{lay}.rels")
    for n in names:
        if n.startswith("ppt/printerSettings/") or n == "docProps/thumbnail.jpeg":
            remove_files.add(n)

    ct = data["[Content_Types].xml"].decode("utf-8")
    for f in remove_files:
        if f.startswith("ppt/slideLayouts/slideLayout") and "_rels" not in f:
            ct = re.sub(r'<Override PartName="/%s"[^/]*/>' % re.escape(f), "", ct)
    ct = re.sub(r'<Override PartName="/docProps/thumbnail\.jpeg"[^/]*/>', "", ct)
    data["[Content_Types].xml"] = ct.encode("utf-8")

    rootrels = data["_rels/.rels"].decode("utf-8")
    rootrels = re.sub(
        r'<Relationship[^>]*Target="docProps/thumbnail\.jpeg"[^/]*/>', "", rootrels
    )
    data["_rels/.rels"] = rootrels.encode("utf-8")

    master_rels_name = "ppt/slideMasters/_rels/slideMaster1.xml.rels"
    master_rels = data[master_rels_name].decode("utf-8")
    dropped_rids = []

    def _drop_rel(m):
        target = m.group("target")
        if "slideLayout" in target and target.split("/")[-1] in {
            f.split("/")[-1] for f in remove_files if "slideLayout" in f and "_rels" not in f
        }:
            dropped_rids.append(m.group("rid"))
            return ""
        if "printerSettings" in target:
            dropped_rids.append(m.group("rid"))
            return ""
        return m.group(0)

    master_rels = re.sub(
        r'<Relationship Id="(?P<rid>[^"]+)"[^>]*Target="(?P<target>[^"]+)"[^/]*/>',
        _drop_rel,
        master_rels,
    )
    data[master_rels_name] = master_rels.encode("utf-8")

    master_name = "ppt/slideMasters/slideMaster1.xml"
    master_xml = data[master_name].decode("utf-8")
    for rid in dropped_rids:
        master_xml = re.sub(
            r'<p:sldLayoutId[^>]*r:id="%s"[^/]*/>' % re.escape(rid), "", master_xml
        )
    data[master_name] = master_xml.encode("utf-8")

    with zipfile.ZipFile(dst_path, "w", zipfile.ZIP_DEFLATED) as out:
        for n in names:
            if n in remove_files:
                continue
            out.writestr(n, data[n])


if __name__ == "__main__":
    strip("petty-cash-pa-digital-proposal.pptx", "petty-cash-pa-digital-proposal-lite.pptx")
