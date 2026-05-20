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
            // 当在这个 Trae 窗口激活文件时，重新把自己的端口写入临时文件
            // 这样就能确保 ASU 永远读取的是“当前正在操作的那个 Trae 窗口”
            if (server && server.address()) {
                const fs = require('fs');
                const path = require('path');
                const os = require('os');
                const portFilePath = path.join(os.tmpdir(), 'asu_ide_port.txt');
                fs.writeFileSync(portFilePath, server.address().port.toString());
            }
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

    server.listen(0, '127.0.0.1', () => {
        const port = server.address().port;
        console.log(`ASU IDE Companion Server running on http://127.0.0.1:${port}`);
        // 将分配到的动态端口写入临时文件，供 ASU 客户端读取
        const fs = require('fs');
        const path = require('path');
        const os = require('os');
        const portFilePath = path.join(os.tmpdir(), 'asu_ide_port.txt');
        
        // 每次启动覆盖写入最新的端口号，并且由于写在临时目录，所有 Trae 实例都会竞争写入
        // 这意味着“最后被激活”的 Trae 窗口的服务端口会生效
        fs.writeFileSync(portFilePath, port.toString());
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
