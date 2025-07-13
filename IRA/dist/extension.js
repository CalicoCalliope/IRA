/******/ (() => { // webpackBootstrap
/******/ 	"use strict";
/******/ 	var __webpack_modules__ = ([
/* 0 */
/***/ (function(__unused_webpack_module, exports, __webpack_require__) {


var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", ({ value: true }));
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(__webpack_require__(1));
const child_process_1 = __webpack_require__(2);
const os = __importStar(__webpack_require__(3));
function activate(context) {
    const logFileUri = vscode.Uri.joinPath(context.globalStorageUri, 'pem-log.json');
    console.log('PEM log file path:', logFileUri.fsPath);
    async function getEnvInfo() {
        return new Promise(resolve => {
            (0, child_process_1.exec)('python --version', (err, stdout) => {
                const pythonVersion = stdout.trim();
                (0, child_process_1.exec)('pip list --format=json', (err2, stdout2) => {
                    resolve({
                        pythonVersion,
                        packages: stdout2
                    });
                });
            });
        });
    }
    async function logPEM(pem) {
        const timestamp = new Date().toISOString();
        const username = os.userInfo().username;
        const editor = vscode.window.activeTextEditor;
        const activeFile = editor?.document.uri.fsPath ?? 'Unknown';
        const workspaceFolders = vscode.workspace.workspaceFolders?.map(f => f.uri.fsPath) ?? [];
        const workingDirectory = workspaceFolders[0] ?? os.homedir();
        const directoryTree = await vscode.workspace.findFiles('**/*', '**/node_modules/**', 100);
        const envInfo = await getEnvInfo();
        const logEntry = {
            timestamp,
            pem,
            username,
            activeFile,
            workingDirectory,
            directoryTree: directoryTree.map(f => vscode.workspace.asRelativePath(f)),
            pythonVersion: envInfo.pythonVersion,
            packages: envInfo.packages ? JSON.parse(envInfo.packages) : [],
        };
        // Read existing entries and append
        let existingEntries = [];
        try {
            const data = await vscode.workspace.fs.readFile(logFileUri);
            existingEntries = JSON.parse(Buffer.from(data).toString('utf8'));
        }
        catch {
            existingEntries = [];
        }
        existingEntries.push(logEntry);
        const updatedData = Buffer.from(JSON.stringify(existingEntries, null, 2), 'utf8');
        await vscode.workspace.fs.writeFile(logFileUri, updatedData);
    }
    // Log diagnostics from LSP (static errors)
    vscode.languages.onDidChangeDiagnostics(event => {
        event.uris.forEach(uri => {
            const diagnostics = vscode.languages.getDiagnostics(uri);
            diagnostics.forEach(diag => {
                if (diag.severity === vscode.DiagnosticSeverity.Error) {
                    logPEM(`[DIAGNOSTIC] ${diag.message}`);
                }
            });
        });
    });
    // Register command to run Python file via Node.js and log runtime errors
    const runPythonAndCaptureErrors = vscode.commands.registerCommand('IRA.runPythonAndCaptureErrors', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor || !editor.document.fileName.endsWith('.py')) {
            vscode.window.showErrorMessage('Open a Python file to run.');
            return;
        }
        const filePath = editor.document.uri.fsPath;
        (0, child_process_1.exec)(`python "${filePath}"`, (error, stdout, stderr) => {
            if (stdout) {
                console.log(`[stdout]: ${stdout}`);
            }
            if (stderr) {
                logPEM(`[RUNTIME ERROR] ${stderr}`);
                vscode.window.showErrorMessage('Runtime error occurred. Logged to .pem-log.txt.');
            }
        });
    });
    context.subscriptions.push(runPythonAndCaptureErrors);
    // Add a button to the status bar
    const runButton = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    runButton.command = 'IRA.runPythonAndCaptureErrors';
    runButton.text = '▶ Run Python (IRA)';
    runButton.tooltip = 'Run current Python file and capture PEMs';
    runButton.show();
    context.subscriptions.push(runButton);
}
function deactivate() { }


/***/ }),
/* 1 */
/***/ ((module) => {

module.exports = require("vscode");

/***/ }),
/* 2 */
/***/ ((module) => {

module.exports = require("child_process");

/***/ }),
/* 3 */
/***/ ((module) => {

module.exports = require("os");

/***/ })
/******/ 	]);
/************************************************************************/
/******/ 	// The module cache
/******/ 	var __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		var cachedModule = __webpack_module_cache__[moduleId];
/******/ 		if (cachedModule !== undefined) {
/******/ 			return cachedModule.exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = __webpack_module_cache__[moduleId] = {
/******/ 			// no module.id needed
/******/ 			// no module.loaded needed
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		__webpack_modules__[moduleId].call(module.exports, module, module.exports, __webpack_require__);
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/************************************************************************/
/******/ 	
/******/ 	// startup
/******/ 	// Load entry module and return exports
/******/ 	// This entry module is referenced by other modules so it can't be inlined
/******/ 	var __webpack_exports__ = __webpack_require__(0);
/******/ 	module.exports = __webpack_exports__;
/******/ 	
/******/ })()
;
//# sourceMappingURL=extension.js.map