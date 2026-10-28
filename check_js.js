const fs = require("fs");
const esprima = require("esprima");

const html = fs.readFileSync("app/templates/payment_memo/index.html", "utf-8");
let scriptContent = "";
const scriptRegex = /<script.*?>([\s\S]*?)<\/script>/gi;
let match;
let counter = 1;

while ((match = scriptRegex.exec(html)) !== null) {
    try {
        esprima.parseScript(match[1]);
        console.log(`Script ${counter}: OK`);
    } catch (e) {
        console.log(`Script ${counter} ERROR at line ${e.lineNumber}: ${e.description}`);
        const lines = match[1].split("\n");
        console.log("Line content:", lines[e.lineNumber - 1].trim());
    }
    counter++;
}
