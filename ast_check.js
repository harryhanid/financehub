const fs = require('fs');
const esprima = require('esprima');

try {
    const content = fs.readFileSync('C:/Financehub/app/static/js/sahabat_etf.js', 'utf8');
    const ast = esprima.parseScript(content);
    let dangling = false;
    for (const node of ast.body) {
        if (node.type !== 'VariableDeclaration' && node.type !== 'FunctionDeclaration' && node.type !== 'ExpressionStatement' && node.type !== 'IfStatement') {
            console.log(node.type);
            dangling = true;
        }
    }
    if (!dangling) console.log("Looks clean at top level.");
} catch(e) {
    console.error("Parse error:", e.message);
}
