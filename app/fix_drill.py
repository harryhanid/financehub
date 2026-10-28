import re
with open("C:/Financehub/app/static/js/sahabat_etf.js", "r", encoding="utf-8") as f:
    content = f.read()

old_drill = """            if (foundChild) {
                node.children = [foundChild];
                node.collapsed = false;
                return true;
            }"""

new_drill = """            if (foundChild) {
                node.children = [foundChild];
                node.collapsed = false;
                
                // If this node has multiple partners, only keep the partner that is in the lineage of the drilled-down child.
                if (node.partners && node.partners.length > 0) {
                    let childId = foundChild.id || '';
                    node.partners = node.partners.filter(p => {
                        let partnerId = p.id || '';
                        // E.g., partnerId is 'A3.4.B', childId is 'A3.4.B.2'
                        if (partnerId && childId.startsWith(partnerId + '.')) {
                            return true;
                        }
                        return false;
                    });
                }
                
                return true;
            }"""

if old_drill in content:
    content = content.replace(old_drill, new_drill)
    with open("C:/Financehub/app/static/js/sahabat_etf.js", "w", encoding="utf-8") as f:
        f.write(content)
    print("Fixed partner filtering in drillDownToUid successfully!")
else:
    print("Could not find drillDownToUid block!")
