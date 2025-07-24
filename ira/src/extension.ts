import * as vscode from 'vscode';
import { exec } from 'child_process';
import * as os from 'os';
import * as path from 'path';
import * as fs from 'fs';
import axios from 'axios';
import * as dotenv from 'dotenv';
import { randomUUID } from 'crypto';

let embedder: any = null;

// Load .env
const envPath = path.resolve(__dirname, '..', '.env');
if (fs.existsSync(envPath)) {
  dotenv.config({ path: envPath });
  console.log('[DEBUG] Loaded .env from:', envPath);
} else {
  console.error('[ERROR] .env file not found at:', envPath);
}

// Environment variables
const openSearchUrl = process.env.OPENSEARCH_CLOUD_URL;
const openSearchUser = process.env.OPENSEARCH_API_USER;
const openSearchPass = process.env.OPENSEARCH_API_PASSWORD;
const qdrantUrl = process.env.QDRANT_URL;
const qdrantKey = process.env.QDRANT_KEY;

if (!openSearchUrl || !openSearchUser || !openSearchPass) {
  console.error('[CONFIG ERROR] OpenSearch credentials are missing.');
}
if (!qdrantUrl || !qdrantKey) {
  console.error('[CONFIG ERROR] Qdrant credentials are missing.');
}

async function getEnvInfo(): Promise<{ pythonVersion?: string, packages?: any[] }> {
  return new Promise(resolve => {
    exec('python --version', (err, stdout) => {
      const pythonVersion = stdout.trim();
      exec('pip list --format=json', (err2, stdout2) => {
        let packages: any[] = [];
        try {
          if (stdout2?.trim()) {
            packages = JSON.parse(stdout2);
          }
        } catch {}
        resolve({ pythonVersion, packages });
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

  let embedding: number[] = [];
  // try {
  //   if (!embedder) {
  //     console.log('[Embedding] Loading model...');
  //     const { pipeline } = await import('@xenova/transformers');
  //     embedder = await pipeline('feature-extraction', 'Xenova/all-MiniLM-L6-v2');
  //   }
  //   const output = await embedder(pem, { pooling: 'mean', normalize: true });
  //   embedding = Array.from(output.data);
  // } catch (e) {
  //   console.error('[Embedding error]', e);
  // }

  const logEntry = {
    timestamp,
    pem,
    username,
    activeFile,
    workingDirectory,
    directoryTree: directoryTree.map(f => vscode.workspace.asRelativePath(f)),
    pythonVersion: envInfo.pythonVersion,
    packages: envInfo.packages,
    embedding
  };

  // --- Log to OpenSearch ---
  try {
    const res = await axios.post(
      `${openSearchUrl}/pems/_doc`,
      logEntry,
      {
        auth: {
          username: openSearchUser!,
          password: openSearchPass!
        },
        headers: { 'Content-Type': 'application/json' }
      }
    );
    console.log('[OpenSearch] PEM logged:', res.data);
  } catch (err: any) {
    console.error('[OpenSearch Error]', err?.response?.data || err.message || err);
  }


  // --- Log to Qdrant ---
  if (embedding.length > 0) {
    try {
      const point = {
        id: randomUUID(),
        vector: embedding,
        payload: {
          pem,
          timestamp,
          username,
          activeFile,
          workingDirectory,
          pythonVersion: envInfo.pythonVersion,
          packages: envInfo.packages
        }
      };

      const res = await axios.put(
        `${qdrantUrl}/collections/pems/points`,
        { points: [point] },
        {
          headers: {
            'Content-Type': 'application/json',
            'api-key': qdrantKey!
          }
        }
      );
      console.log('[Qdrant] PEM logged:', res.data);
    } catch (err: any) {
      console.error('[Qdrant Error]', err?.response?.data || err.message);
    }
  } else {
    console.warn('[Qdrant] Skipped logging — embedding unavailable.');
  }
}

export function activate(context: vscode.ExtensionContext) {
  // Register command to run Python and capture PEMs
  const runAndCaptureErrors = vscode.commands.registerCommand('IRA.runPythonAndCaptureErrors', async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor || !editor.document.fileName.endsWith('.py')) {
      vscode.window.showErrorMessage('Open a Python file to run.');
      return;
    }

    const filePath = editor.document.uri.fsPath;
    exec(`python "${filePath}"`, async (error, stdout, stderr) => {
      if (stdout) {
        console.log(`[stdout]: ${stdout}`);
      }
      if (stderr) {
        await logPEM(`[RUNTIME ERROR] ${stderr}`);
        vscode.window.showErrorMessage('Runtime error occurred. Logged to PEM history.');
      }
    });
  });
  context.subscriptions.push(runAndCaptureErrors);

  // Add a button to the status bar
  const runButton = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  runButton.command = 'IRA.runPythonAndCaptureErrors';
  runButton.text = '▶ Run Python (IRA)';
  runButton.tooltip = 'Run current Python file and capture PEMs';
  runButton.show();
  context.subscriptions.push(runButton);
}

export function deactivate() {}