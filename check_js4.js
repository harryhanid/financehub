const fs = require("fs");
const esprima = require("esprima");

const html = fs.readFileSync("rendered.html", "utf-8");
const scriptRegex = /<script.*?>([\s\S]*?)<\/script>/gi;
let match;
let counter = 1;

while ((match = scriptRegex.exec(html)) !== null) {
    let js = match[1];
    
    // We pad the js with newlines so the line numbers match the HTML document!
    let linesBefore = html.substring(0, match.index).split("\n").length;
    let paddedJs = "\n".repeat(linesBefore) + js;

    try {
        esprima.parseScript(paddedJs);
        console.log(`Script ${counter} (starting around line ${linesBefore}): OK`);
    } catch (e) {
        console.log(`Script ${counter} ERROR at line ${e.lineNumber}: ${e.description}`);
        const lines = paddedJs.split("\n");
        console.log("Line content:", lines[e.lineNumber - 1].trim());
    }
    counter++;
}
