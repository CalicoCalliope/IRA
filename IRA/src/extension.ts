import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as os from 'os';
import * as path from 'path';

export function activate(context: vscode.ExtensionContext) {
  const logFileUri = vscode.Uri.joinPath(context.globalStorageUri, 'pem-log.json');
	console.log('PEM log file path:', logFileUri.fsPath);

  async function getEnvInfo(): Promise<{ pythonVersion?: string, packages?: string }> {
    return new Promise(resolve => {
      exec('python --version', (err, stdout) => {
        const pythonVersion = stdout.trim();
        exec('pip list --format=json', (err2, stdout2) => {
          resolve({
            pythonVersion,
            packages: stdout2
          });
        });
      });
    });
  }

	async function logPEM(pem: string) {
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
    } catch {
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
    exec(`python "${filePath}"`, (error, stdout, stderr) => {
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

export function deactivate() {}