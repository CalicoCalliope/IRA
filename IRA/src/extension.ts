import * as vscode from 'vscode';
import { exec } from 'child_process';

export function activate(context: vscode.ExtensionContext) {
	console.log('PEM log file path:', vscode.Uri.joinPath(context.globalStorageUri, '.pem-log.txt').fsPath);

	function logPEM(message: string) {
		const logEntry = `${new Date().toISOString()} - ${message}\n`;
		const logFileUri = vscode.Uri.joinPath(context.globalStorageUri, '.pem-log.txt');
		vscode.workspace.fs.readFile(logFileUri).then(
			data => {
				const existing = Buffer.from(data).toString('utf8');
				const updated = existing + logEntry;
				return vscode.workspace.fs.writeFile(logFileUri, Buffer.from(updated, 'utf8'));
			},
			() => {
				return vscode.workspace.fs.writeFile(logFileUri, Buffer.from(logEntry, 'utf8'));
			}
		);
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
}

export function deactivate() {}