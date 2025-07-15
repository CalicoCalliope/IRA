"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/extension.ts
var extension_exports = {};
__export(extension_exports, {
  activate: () => activate,
  deactivate: () => deactivate
});
module.exports = __toCommonJS(extension_exports);
var vscode = __toESM(require("vscode"));
var import_child_process = require("child_process");
var os = __toESM(require("os"));
function activate(context) {
  const logFileUri = vscode.Uri.joinPath(context.globalStorageUri, "pem-log.json");
  console.log("PEM log file path:", logFileUri.fsPath);
  async function getEnvInfo() {
    return new Promise((resolve) => {
      (0, import_child_process.exec)("python --version", (err, stdout) => {
        const pythonVersion = stdout.trim();
        (0, import_child_process.exec)("pip list --format=json", (err2, stdout2) => {
          resolve({
            pythonVersion,
            packages: stdout2
          });
        });
      });
    });
  }
  async function logPEM(pem) {
    const timestamp = (/* @__PURE__ */ new Date()).toISOString();
    const username = os.userInfo().username;
    const editor = vscode.window.activeTextEditor;
    const activeFile = editor?.document.uri.fsPath ?? "Unknown";
    const workspaceFolders = vscode.workspace.workspaceFolders?.map((f) => f.uri.fsPath) ?? [];
    const workingDirectory = workspaceFolders[0] ?? os.homedir();
    const directoryTree = await vscode.workspace.findFiles("**/*", "**/node_modules/**", 100);
    const envInfo = await getEnvInfo();
    const logEntry = {
      timestamp,
      pem,
      username,
      activeFile,
      workingDirectory,
      directoryTree: directoryTree.map((f) => vscode.workspace.asRelativePath(f)),
      pythonVersion: envInfo.pythonVersion,
      packages: envInfo.packages ? JSON.parse(envInfo.packages) : []
    };
    let existingEntries = [];
    try {
      const data = await vscode.workspace.fs.readFile(logFileUri);
      existingEntries = JSON.parse(Buffer.from(data).toString("utf8"));
    } catch {
      existingEntries = [];
    }
    existingEntries.push(logEntry);
    const updatedData = Buffer.from(JSON.stringify(existingEntries, null, 2), "utf8");
    await vscode.workspace.fs.writeFile(logFileUri, updatedData);
  }
  vscode.languages.onDidChangeDiagnostics((event) => {
    event.uris.forEach((uri) => {
      const diagnostics = vscode.languages.getDiagnostics(uri);
      diagnostics.forEach((diag) => {
        if (diag.severity === vscode.DiagnosticSeverity.Error) {
          logPEM(`[DIAGNOSTIC] ${diag.message}`);
        }
      });
    });
  });
  const runPythonAndCaptureErrors = vscode.commands.registerCommand("IRA.runPythonAndCaptureErrors", async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor || !editor.document.fileName.endsWith(".py")) {
      vscode.window.showErrorMessage("Open a Python file to run.");
      return;
    }
    const filePath = editor.document.uri.fsPath;
    (0, import_child_process.exec)(`python "${filePath}"`, (error, stdout, stderr) => {
      if (stdout) {
        console.log(`[stdout]: ${stdout}`);
      }
      if (stderr) {
        logPEM(`[RUNTIME ERROR] ${stderr}`);
        vscode.window.showErrorMessage("Runtime error occurred. Logged to .pem-log.txt.");
      }
    });
  });
  context.subscriptions.push(runPythonAndCaptureErrors);
  const runButton = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  runButton.command = "IRA.runPythonAndCaptureErrors";
  runButton.text = "\u25B6 Run Python (IRA)";
  runButton.tooltip = "Run current Python file and capture PEMs";
  runButton.show();
  context.subscriptions.push(runButton);
}
function deactivate() {
}
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  activate,
  deactivate
});
//# sourceMappingURL=extension.js.map
