import sys

def patch_js():
    with open(r'C:\Financehub\app\static\js\sahabat_etf.js', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add setfGetContrastYIQ function at the top
    yiq_func = """function setfGetContrastYIQ(hexcolor){
  if (!hexcolor) return 'light';
  hexcolor = hexcolor.replace("#", "");
  if (hexcolor.length === 3) {
     hexcolor = hexcolor.split('').map(c => c+c).join('');
  }
  var r = parseInt(hexcolor.substr(0,2),16);
  var g = parseInt(hexcolor.substr(2,2),16);
  var b = parseInt(hexcolor.substr(4,2),16);
  var yiq = ((r*299)+(g*587)+(b*114))/1000;
  return (yiq >= 128) ? 'dark' : 'light';
}

function setfColorForCategory"""
    if "function setfGetContrastYIQ" not in content:
        content = content.replace("function setfColorForCategory", yiq_func)

    # 2. Replace the datalabels config in setfRenderStackedGroupedChart
    old_datalabels = """        datalabels: {
          display: function(context) {
             return context.dataset.data[context.dataIndex] > 0;
          },
          align: 'center',
          anchor: 'center',
          color: '#fff',
          font: { size: 9, weight: 'bold' },
          formatter: function(value) {
            return setfFmtJutaan(value);
          }
        },"""

    new_datalabels = """        datalabels: {
          display: function(context) {
             const val = context.dataset.data[context.dataIndex];
             if (!val || val <= 0) return false;
             
             // Hide if segment is too small to fit text (< 5% of total stack)
             const meta = context.chart.getDatasetMeta(context.datasetIndex);
             const stackId = meta.stack;
             let sum = 0;
             context.chart.data.datasets.forEach((ds, i) => {
                 const m = context.chart.getDatasetMeta(i);
                 if (m.stack === stackId) {
                     sum += (ds.data[context.dataIndex] || 0);
                 }
             });
             return sum > 0 && (val / sum) > 0.06;
          },
          align: 'center',
          anchor: 'center',
          color: function(context) {
             const bg = context.dataset.backgroundColor;
             return setfGetContrastYIQ(bg) === 'dark' ? '#0f172a' : '#ffffff';
          },
          font: { size: 9, weight: 'bold' },
          formatter: function(value) {
            return setfFmtJutaan(value);
          }
        },"""

    if old_datalabels in content:
        content = content.replace(old_datalabels, new_datalabels)
        with open(r'C:\Financehub\app\static\js\sahabat_etf.js', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patched sahabat_etf.js")
    else:
        print("Could not find datalabels block to patch")

if __name__ == '__main__':
    patch_js()
