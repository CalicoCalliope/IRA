import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as os from 'os';
import * as path from 'path';
import axios from 'axios';
import * as dotenv from 'dotenv';
import * as fs from 'fs';

let embedder: any = null;

const envPath = path.resolve(__dirname, '..', '.env');
if (fs.existsSync(envPath)) {
  dotenv.config({ path: envPath });
  console.log('[DEBUG] Loaded .env from:', envPath);
} else {
  console.error('[ERROR] .env file not found at:', envPath);
}

export async function getEmbedding(text: string): Promise<number[]> {
  try {
    if (!embedder) {
      console.log('Loading embedding model...');
      const { pipeline } = await import('@xenova/transformers');
      embedder = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2');
    }

    const output = await embedder(text, { pooling: 'mean', normalize: true });
    return Array.from(output.data);
  } catch (err) {
    console.error('Embedding error:', err);
    return [];
  }
}

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
    // const embedding = await getEmbedding(pem);
    const embedding: number[] = []; // temporary fix bc xenova doesn't work rn

    const logEntry = {
      timestamp,
      pem,
      username,
      activeFile,
      workingDirectory,
      directoryTree: directoryTree.map(f => vscode.workspace.asRelativePath(f)),
      pythonVersion: envInfo.pythonVersion,
      packages: envInfo.packages ? JSON.parse(envInfo.packages) : [],
      embedding
    };

    const adminPassword = process.env.OPENSEARCH_INITIAL_ADMIN_PASSWORD;
    if (!adminPassword) {
      throw new Error('Missing OPENSEARCH_INITIAL_ADMIN_PASSWORD in .env');
    }
    const password: string = adminPassword;

    try {
      const res = await axios.post(
        'https://localhost:9200/pems/_doc',
        logEntry,
        {
          auth: {
            username: 'admin',
            password: password
          },
          headers: { 'Content-Type': 'application/json' },
          httpsAgent: new (require('https').Agent)({ rejectUnauthorized: false }) // allows self-signed certs
        }
      );
      console.log('PEM logged to OpenSearch:', res.data);
    } catch (err) {
      console.error('Error logging PEM to OpenSearch:', err);
    }
  }

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
        vscode.window.showErrorMessage('Runtime error occurred. Saved to history.');
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