export interface ArticleInput {
  type: 'url' | 'text';
  content: string;
}

export interface ArticleMetadata {
  title: string;
  url: string;
  publisher?: string;
  journalist?: string;
  publishDate?: string;
  articleType?: string;
  originalUrl?: string;
  articleElements?: string;
  editStructure?: string;
  reportingMethod?: string;
  contentFlow?: string;
}

export interface AnalysisReport {
  comprehensive: string;
  journalist: string;
  student: string;
}

export interface AnalysisResult {
  article_info: ArticleMetadata;
  reports: AnalysisReport;
}

export type AnalysisPhase = 'scanning' | 'analyzing' | 'complete';