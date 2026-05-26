const vscode = require('vscode');
const http = require('http');
const fs = require('fs');
const path = require('path');
const os = require('os');

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
            // 这样就能确保 ASU 永远读取的是"当前正在操作的那个 Trae 窗口"
            if (server && server.address()) {
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
        res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
        res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

        if (req.method === 'OPTIONS') {
            res.writeHead(204);
            res.end();
            return;
        }

        // GET /context — 读取当前文件全文
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
        }
        // POST /apply — 将修改内容回写到 IDE 编辑器
        else if (req.method === 'POST' && req.url === '/apply') {
            let body = '';
            req.on('data', chunk => { body += chunk; });
            req.on('end', () => {
                try {
                    const data = JSON.parse(body);
                    const editor = vscode.window.activeTextEditor;
                    if (!editor) {
                        res.writeHead(400, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({ error: 'No active editor' }));
                        return;
                    }

                    const fullText = data.content;
                    const range = data.range; // 可选: {startLine, startCol, endLine, endCol}
                    const replaceText = data.replace; // 可选: 替换文本（局部替换时使用）

                    if (replaceText !== undefined && range) {
                        // 局部替换模式：替换指定范围内的文本
                        const startLine = Math.max(0, (range.startLine || 0));
                        const startCol = Math.max(0, (range.startCol || 0));
                        const endLine = Math.max(0, (range.endLine || 0));
                        const endCol = Math.max(0, (range.endCol || 0));

                        const startPos = new vscode.Position(startLine, startCol);
                        const endPos = new vscode.Position(endLine, endCol);
                        const editRange = new vscode.Range(startPos, endPos);

                        editor.edit(editBuilder => {
                            editBuilder.replace(editRange, replaceText);
                        }).then(success => {
                            res.writeHead(200, { 'Content-Type': 'application/json' });
                            res.end(JSON.stringify({ success: success, mode: 'partial' }));
                        });
                    } else if (fullText !== undefined) {
                        // 全文替换模式：替换整个文件内容
                        const doc = editor.document;
                        const fullRange = new vscode.Range(
                            doc.lineAt(0).range.start,
                            doc.lineAt(doc.lineCount - 1).range.end
                        );

                        editor.edit(editBuilder => {
                            editBuilder.replace(fullRange, fullText);
                        }).then(success => {
                            res.writeHead(200, { 'Content-Type': 'application/json' });
                            res.end(JSON.stringify({ success: success, mode: 'full' }));
                        });
                    } else {
                        res.writeHead(400, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({ error: 'Missing content or replace field' }));
                    }
                } catch (e) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Invalid JSON: ' + e.message }));
                }
            });
        }
        // POST /selection — 读取当前选中文本
        else if (req.method === 'GET' && req.url === '/selection') {
            const editor = vscode.window.activeTextEditor;
            if (!editor || editor.selection.isEmpty) {
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ text: '', range: null }));
                return;
            }
            const sel = editor.selection;
            const text = editor.document.getText(sel);
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                text: text,
                range: {
                    startLine: sel.start.line,
                    startCol: sel.start.character,
                    endLine: sel.end.line,
                    endCol: sel.end.character
                },
                fileName: editor.document.fileName,
                languageId: editor.document.languageId
            }));
        }
        else {
            res.writeHead(404, { 'Content-Type': 'text/plain' });
            res.end('Not Found');
        }
    });

    server.listen(0, '127.0.0.1', () => {
        const port = server.address().port;
        console.log(`ASU IDE Companion Server running on http://127.0.0.1:${port}`);
        // 将分配到的动态端口写入临时文件，供 ASU 客户端读取
        const portFilePath = path.join(os.tmpdir(), 'asu_ide_port.txt');
        
        // 每次启动覆盖写入最新的端口号，并且由于写在临时目录，所有 Trae 实例都会竞争写入
        // 这意味着"最后被激活"的 Trae 窗口的服务端口会生效
        fs.writeFileSync(portFilePath, port.toString());
    });
    
    server.on('error', (e) => {
        console.error('Failed to start ASU IDE Server:', e);
        const port = server?.address()?.port || '(unknown)';
        vscode.window.showErrorMessage(`ASU IDE Companion failed to start on port ${port}: ${e.message}`);
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
