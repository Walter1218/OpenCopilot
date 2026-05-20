const vscode = require('vscode');
const http = require('http');

let server;
let lastActiveDocument = null;

function activate(context) {
    console.log('ASU IDE Companion extension is now active!');

    // 记录最后一次激活的真实文件，防止失去焦点后 activeTextEditor 变 undefined
    if (vscode.window.activeTextEditor) {
        lastActiveDocument = vscode.window.activeTextEditor.document;
    }

    let activeEditorDisposable = vscode.window.onDidChangeActiveTextEditor(editor => {
        if (editor && editor.document && editor.document.uri.scheme === 'file') {
            lastActiveDocument = editor.document;
        }
    });
    context.subscriptions.push(activeEditorDisposable);

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
    // 如果在重启插件时端口仍被占用，强制关闭之前的服务器实例
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
            // 优先获取当前激活的，如果没有（比如焦点在外部窗口），则使用我们记录的最后一个激活文件
            let document = null;
            if (vscode.window.activeTextEditor && vscode.window.activeTextEditor.document.uri.scheme === 'file') {
                document = vscode.window.activeTextEditor.document;
                lastActiveDocument = document; // 更新缓存
            } else if (lastActiveDocument) {
                document = lastActiveDocument;
            }
            
            if (!document) {
                res.writeHead(404, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'No active or recent editor found' }));
                return;
            }

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
