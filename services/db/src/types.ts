export interface PemLogEntry {
  id: string;
  timestamp: string;
  pem: string;
  pemType: string;
  pemSkeleton: string;
  code: string;
  username: string;
  activeFile: string;
  workingDirectory: string;
  directoryTree: string[];
  pythonVersion?: string;
  packages?: any[];
  isFirstOccurrence: boolean;
  llm: {
    hint?: string;
    reasoning?: string;
    answer?: string;
  };
  accessed:{
    hint?: boolean;
    reasoning?: boolean;
    answer?: boolean;
  };
  hraEvents?: {
    type: "hint" | "reasoning" | "answer";
    timestamp: string; // ISO string
  }[];
}

export interface UserEvent {
  type: 'file_closed';
  timestamp: string;
  username: string;
  file: string;
}
