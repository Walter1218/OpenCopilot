const vscode = require('vscode');
const http = require('http');

let server;

function activate(context) {
    console.log('ASU IDE Companion extension is now active!');

    // Command to manually start the server if needed
    let disposable = vscode.commands.registerCommand('asu-ide-extension.startServer', function () {
        startServer();
    });
    context.subscriptions.push(disposable);

    // Auto-start the server when extension activates
    startServer();

    context.subscriptions.push({
        dispose: () => {
            if (server) {
                server.close();
            }
        }
    });
}

function startServer() {
    if (server) {
        server.close();
    }

    server = http.createServer((req, res) => {
        // Set CORS headers
        res.setHeader('Access-Control-Allow-Origin', '*');
        res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

        if (req.method === 'OPTIONS') {
            res.writeHead(204);
            res.end();
            return;
        }

        if (req.method === 'GET' && req.url === '/context') {
            // 在 VSCode API 中获取所有打开的文本文档
            const docs = vscode.workspace.textDocuments.filter(doc => doc.uri.scheme === 'file');
            
            if (docs.length === 0) {
                res.writeHead(404, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'No files are currently open in the workspace' }));
                return;
            }

            // 获取最后一个被修改或打开的真实文件
            const document = docs[docs.length - 1];

            const text = document.getText();
            const fileName = document.fileName;
            const languageId = document.languageId;

            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                fileName: fileName,
                languageId: languageId,
                content: text
            }));
        } else {
            res.writeHead(404, { 'Content-Type': 'text/plain' });
            res.end('Not Found');
        }
    });

    server.listen(18889, '127.0.0.1', () => {
        console.log('ASU IDE Companion Server running on http://127.0.0.1:18889');
    });
    
    server.on('error', (e) => {
        console.error('Failed to start ASU IDE Server:', e);
        vscode.window.showErrorMessage(`ASU IDE Companion failed to start on port 18889: ${e.message}`);
    });
}

function deactivate() {
    if (server) {
        server.close();
    }
}

module.exports = {
    activate,
    deactivate
};
