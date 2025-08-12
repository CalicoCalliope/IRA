import * as vscode from 'vscode';
import { exec } from 'child_process';
import { spawn } from 'child_process';
import * as os from 'os';
import * as path from 'path';
import * as fs from 'fs';
import axios from 'axios';
import * as dotenv from 'dotenv';
import { randomUUID } from 'crypto';
import { MongoClient } from "mongodb";
import { Collection } from "mongodb";

let embedder: any = null;

interface PemLogEntry {
  _id: string;
  timestamp: string;
  pem: string;
  pemType: string;
  username: string;
  activeFile: string;
  workingDirectory: string;
  directoryTree: string[];
  pythonVersion?: string;
  packages?: any[];
  isFirstOccurrence: boolean;
  pemSkeleton: string;
}

// Load .env
const envPath = path.resolve(__dirname, '..', '.env');
if (fs.existsSync(envPath)) {
  dotenv.config({ path: envPath });
  console.log('[DEBUG] Loaded .env from:', envPath);
} else {
  console.error('[ERROR] .env file not found at:', envPath);
}

// Environment variables
const uri = process.env.MONGODB_URI!;
const qdrantUrl = process.env.QDRANT_URL;
const qdrantKey = process.env.QDRANT_KEY;

if (!uri) {
  console.error('[CONFIG ERROR] MongoDB credentials are missing.');
  throw new Error("MONGODB_URI is required but not set.");
}
if (!qdrantUrl || !qdrantKey) {
  console.error('[CONFIG ERROR] Qdrant credentials are missing.');
}

let clientDB: MongoClient | null = null;

export async function getClient(): Promise<MongoClient> {
  if (clientDB) {
    return clientDB;
  }

  clientDB = new MongoClient(uri);
  await clientDB.connect();
  return clientDB;
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

function extractPemType(errorMessage: string): string {
  const match = errorMessage.match(/([a-zA-Z]+Error)/);
  return match ? match[1] : "UnknownError";
}

function getPemSkeletonFromPython(pem: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(__dirname, '..', 'scripts', 'pem_parser.py');
    const python = spawn('python', [scriptPath]);

    let output = '';
    let error = '';

    python.stdout.on('data', (data) => {
      output += data.toString();
    });

    python.stderr.on('data', (data) => {
      error += data.toString();
    });

    python.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Python script exited with code ${code}: ${error}`));
      } else {
        try {
          const parsed = JSON.parse(output);
          resolve(parsed.pemSkeleton);
        } catch (err) {
          reject(new Error(`Failed to parse JSON from Python script: ${err}`));
        }
      }
    });

    python.stdin.write(pem);
    python.stdin.end();
  });
}

function getEmbeddingFromPython(codeSnippet: string): Promise<number[]> {
    return new Promise((resolve, reject) => {
        const scriptPath = path.join(__dirname, '..', 'scripts', 'CuBERT', 'CuBERT2.py');

        const pyProcess = spawn('python', [scriptPath], { stdio: ['pipe', 'pipe', 'pipe'] });

        let output = '';
        let errorOutput = '';

        pyProcess.stdout.on('data', data => output += data.toString());
        pyProcess.stderr.on('data', data => errorOutput += data.toString());

        pyProcess.on('close', () => {
            try {
                const parsed = JSON.parse(output);
                if (parsed.error) {
                    reject(parsed.error);
                } else {
                    resolve(parsed.embedding);
                }
            } catch (err) {
                reject(new Error(`Failed to parse embedding: ${err} | stderr: ${errorOutput}`));
            }
        });

        pyProcess.stdin.write(codeSnippet);
        pyProcess.stdin.end();
    });
}

async function logPEM(pem: string, pemType: string) {
  const id = randomUUID();
  const timestamp = new Date().toISOString();
  const username = os.userInfo().username;
  const editor = vscode.window.activeTextEditor;
  const activeFile = editor?.document.uri.fsPath ?? 'Unknown';
  const workspaceFolders = vscode.workspace.workspaceFolders?.map(f => f.uri.fsPath) ?? [];
  const workingDirectory = workspaceFolders[0] ?? os.homedir();
  const directoryTree = await vscode.workspace.findFiles('**/*', '**/node_modules/**', 100);
  const envInfo = await getEnvInfo();
  const pemSkeleton = await getPemSkeletonFromPython(pem);

  const clientDB = await getClient();
  const db = clientDB.db("iraLogs");
  const collection: Collection<PemLogEntry> = db.collection<PemLogEntry>("pems");

  const prior = await collection.findOne({ username, pemType });
  const isFirstOccurrence = prior === null;

  let embedding: number[] = [];
  try {
      embedding = await getEmbeddingFromPython(pem);
      console.log('[Embedding] Received from Python:', embedding.length);
  } catch (e) {
      console.error('[Embedding Error]', e);
  }

  const logEntry = {
    _id: id,
    timestamp,
    pem,
    pemType,
    pemSkeleton,
    username,
    activeFile,
    workingDirectory,
    directoryTree: directoryTree.map(f => vscode.workspace.asRelativePath(f)),
    pythonVersion: envInfo.pythonVersion,
    packages: envInfo.packages,
    isFirstOccurrence
  };

  // --- Log to MongoDB ---
  try {
    const result = await collection.insertOne(logEntry);
    console.log('[MongoDB] PEM logged with ID:', result.insertedId);
  } catch (err: any) {
    console.error('[MongoDB Error]', err.message);
  }


  // --- Log to Qdrant ---
  if (embedding.length > 0) {
    try {
      const point = {
        id: id,
        vector: embedding,
        payload: {
          timestamp,
          username,
          pemType
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
      console.log('[Qdrant] Embedding logged:', res.data);
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
      const pem = `[RUNTIME ERROR] ${stderr}`;
      const pemType = extractPemType(stderr); // Extract directly from raw error string
      await logPEM(pem, pemType);
      vscode.window.showErrorMessage(`Runtime error (${pemType}) occurred. Logged to PEM history.`);
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

export function deactivate() {
  if (clientDB) {
    clientDB.close().catch(console.error);
  }
}