file_path = "C:/Financehub/app/static/js/sahabat_etf.js"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = """      },
    },
        },
      plugins: {"""
repl = """      },
    },
  });
}
"""

# Wait, let's see what is after `plugins: {`... It looks like a whole new `options` block was injected but not correctly replacing the old one!
# Let's see the lines around 337 using re.
import re
match = re.search(r'y: \{\s*stacked: true,\s*ticks: \{[^\}]+\},\s*grid: \{[^\}]+\},\s*\},\s*\},\s*\},\s*\}\);\s*\},[\s\S]*?plugins: \{', content)
if match:
    print("Found match!")
else:
    print("Not found with regex")
