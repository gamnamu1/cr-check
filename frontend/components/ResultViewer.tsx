import { useState } from 'react';
import { motion } from 'motion/react';
import { ExternalLink, FileDown, ArrowLeft, Users, NotebookPen, BookOpenCheck, Newspaper } from 'lucide-react';
import type { AnalysisResult } from '../types';
import { TxtPreviewModal } from './TxtPreviewModal';

interface ResultViewerProps {
  result: AnalysisResult;
  onReset: () => void;
}

type ReportTab = 'comprehensive' | 'journalist' | 'student';

export function ResultViewer({ result, onReset }: ResultViewerProps) {
  const [activeTab, setActiveTab] = useState<ReportTab>('comprehensive');
  const [showPreviewModal, setShowPreviewModal] = useState(false);

  const tabs = [
    { id: 'comprehensive' as ReportTab, label: '시민을 위한 종합 리포트', shortLabel: '시민', icon: Users, color: 'navy' },
    { id: 'journalist' as ReportTab, label: '기자를 위한 전문 리포트', shortLabel: '기자', icon: NotebookPen, color: 'amber' },
    { id: 'student' as ReportTab, label: '학생을 위한 교육 리포트', shortLabel: '학생', icon: BookOpenCheck, color: 'navy' },
  ];

  const formatContent = (content: string) => {
    // Convert markdown-style content to HTML-like JSX
    const lines = content.split('\n');
    const elements: JSX.Element[] = [];
    let key = 0;

    // Helper to highlight ethics codes
    const highlightEthics = (text: string) => {
      // Regex to match various ethics codes followed by optional quote
      // Includes: 언론윤리헌장, 한국기자협회 강령, 언론윤리강령/실천요강, 신문윤리강령/실천요강, etc.
      const ethicsPattern = /(?:언론윤리헌장|한국기자협회\s*강령|언론윤리(?:강령|실천요강)|신문윤리(?:강령|실천요강)|자살보도\s*윤리강령|인권보도준칙|자살예방\s*보도준칙|재난보도준칙|선거여론조사\s*보도준칙)/;

      // Split by the pattern, capturing the code name and following content up to the end of the quote if present
      // We look for the pattern, followed by non-newline characters, optionally ending with a quote
      const parts = text.split(/((?:언론윤리헌장|한국기자협회\s*강령|언론윤리(?:강령|실천요강)|신문윤리(?:강령|실천요강)|자살보도\s*윤리강령|인권보도준칙|자살예방\s*보도준칙|재난보도준칙|선거여론조사\s*보도준칙)[^"\n]*(?:"[^"]*")?)/g);

      return parts.map((part, idx) => {
        if (ethicsPattern.test(part)) {
          return (
            <span key={idx} className="text-[#4682b4] font-sans font-normal">
              {part}
            </span>
          );
        }
        // Handle bold text within normal text
        if (part.includes('**')) {
          const boldParts = part.split(/(\*\*.*?\*\*)/g);
          return (
            <span key={idx}>
              {boldParts.map((bp, bIdx) => {
                if (bp.startsWith('**') && bp.endsWith('**')) {
                  return <strong key={bIdx} className="text-navy-900 font-bold">{bp.slice(2, -2)}</strong>;
                }
                return <span key={bIdx}>{bp}</span>;
              })}
            </span>
          );
        }
        return <span key={idx}>{part}</span>;
      });
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // H1
      if (line.startsWith('# ')) {
        elements.push(
          <h2 key={key++} className="text-navy-900 mt-8 mb-4 first:mt-0 font-sans font-bold text-2xl">
            {line.replace('# ', '')}
          </h2>
        );
      }
      // H2
      else if (line.startsWith('## ')) {
        elements.push(
          <h3 key={key++} className="text-navy-800 mt-6 mb-3 font-sans font-bold text-xl">
            {line.replace('## ', '')}
          </h3>
        );
      }
      // H3
      else if (line.startsWith('### ')) {
        elements.push(
          <h4 key={key++} className="text-navy-700 mt-4 mb-2 font-sans font-semibold text-lg">
            {line.replace('### ', '')}
          </h4>
        );
      }
      // Code block
      else if (line.startsWith('```')) {
        const codeLines: string[] = [];
        i++;
        while (i < lines.length && !lines[i].startsWith('```')) {
          codeLines.push(lines[i]);
          i++;
        }
        elements.push(
          <pre key={key++} className="bg-navy-900 text-white p-4 rounded-lg my-4 overflow-x-auto font-mono text-sm">
            <code>{codeLines.join('\n')}</code>
          </pre>
        );
      }
      // List item
      else if (line.startsWith('- ') || line.startsWith('* ')) {
        const listItems: string[] = [line];
        while (i + 1 < lines.length && (lines[i + 1].startsWith('- ') || lines[i + 1].startsWith('* '))) {
          i++;
          listItems.push(lines[i]);
        }
        elements.push(
          <ul key={key++} className="list-disc list-inside space-y-2 my-4 text-navy-700 font-serif leading-loose">
            {listItems.map((item, idx) => (
              <li key={idx}>{highlightEthics(item.replace(/^[*-] /, ''))}</li>
            ))}
          </ul>
        );
      }
      // Regular paragraph (including bold text lines)
      else if (line.trim()) {
        elements.push(
          <p key={key++} className="text-navy-700 leading-loose my-3 font-serif text-lg">
            {highlightEthics(line)}
          </p>
        );
      }
      // Empty line
      else {
        elements.push(<div key={key++} className="h-2" />);
      }
    }

    return elements;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-navy-50 via-white to-amber-50">
      {/* Header */}
      <header className="border-b border-navy-200 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="mx-auto max-w-7xl px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={onReset}
                className="flex items-center gap-2 text-navy-600 hover:text-navy-900 transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
                <span>다른 기사 분석</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8">
        {/* Article Overview Card */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl shadow-lg border border-navy-100 p-8 mb-8"
        >
          <div className="flex items-start justify-between gap-4 mb-6">
            <div className="flex items-center gap-2" style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans KR", sans-serif' }}>
              <Newspaper className="w-5 h-5 text-navy-700" />
              <h3 className="text-navy-900 font-[Noto_Serif] text-[20px]">기사 정보</h3>
            </div>
            {result.article_info.url && (
              <a
                href={result.article_info.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2 bg-navy-900 text-white rounded-lg hover:bg-navy-800 transition-colors shrink-0"
              >
                <ExternalLink className="w-4 h-4" />
                <span className="hidden sm:inline">원문 보기</span>
              </a>
            )}
          </div>

          <div className="space-y-4 text-navy-700">
            <div>
              <p className="text-sm">
                <strong className="text-navy-900">기사 제목:</strong> {result.article_info.title}
              </p>
            </div>

            <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm pt-4 border-t border-navy-100">
              <span><strong className="text-navy-900">매체명:</strong> {result.article_info.publisher || '미확인'}</span>
              <span><strong className="text-navy-900">게재일시:</strong> {result.article_info.publishDate || '미확인'}</span>
              <span><strong className="text-navy-900">기자명:</strong> {result.article_info.journalist || '미확인'}</span>
            </div>

            <div className="grid md:grid-cols-2 gap-4 pt-4 border-t border-navy-100">
              <div>
                <p className="text-sm">
                  <strong className="text-navy-900">기사 유형:</strong> {result.article_info.articleType || '일반 기사'}
                </p>
              </div>
              {result.article_info.articleElements && (
                <div>
                  <p className="text-sm">
                    <strong className="text-navy-900">기사 요소:</strong> {result.article_info.articleElements}
                  </p>
                </div>
              )}
              {result.article_info.editStructure && (
                <div>
                  <p className="text-sm">
                    <strong className="text-navy-900">편집 구조:</strong> {result.article_info.editStructure}
                  </p>
                </div>
              )}
              {result.article_info.reportingMethod && (
                <div>
                  <p className="text-sm">
                    <strong className="text-navy-900">취재 방식:</strong> {result.article_info.reportingMethod}
                  </p>
                </div>
              )}
            </div>

            {result.article_info.contentFlow && (
              <div className="pt-4 border-t border-navy-100">
                <p className="text-sm">
                  <strong className="text-navy-900">내용 흐름:</strong> {result.article_info.contentFlow}
                </p>
              </div>
            )}
          </div>
        </motion.div>

        {/* Report Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-2xl shadow-lg border border-navy-100 overflow-hidden mb-8"
        >
          {/* Tab Headers */}
          <div className="grid grid-cols-3 border-b border-navy-100">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-6 py-4 flex items-center justify-center gap-2 transition-all relative ${isActive
                    ? 'bg-navy-700 text-white'
                    : 'bg-white text-navy-600 hover:bg-navy-50'
                    }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="hidden md:inline">{tab.label}</span>
                  <span className="md:hidden">{tab.shortLabel}</span>
                </button>
              );
            })}
          </div>

          {/* Tab Content */}
          <div className="p-8 md:p-12">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3 }}
              className="prose prose-lg max-w-none custom-scrollbar"
            >
              {formatContent(result.reports[activeTab])}
            </motion.div>
          </div>
        </motion.div>

        {/* Action Bar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex flex-col sm:flex-row gap-4 justify-center"
        >
          <button
            onClick={() => setShowPreviewModal(true)}
            className="flex items-center justify-center gap-2 px-8 py-4 bg-amber-500 hover:bg-amber-600 text-white rounded-xl transition-all transform hover:scale-[1.02]"
          >
            <FileDown className="w-5 h-5" />
            <span>리포트 문서 저장 (TXT)</span>
          </button>
          <button
            onClick={onReset}
            className="flex items-center justify-center gap-2 px-8 py-4 bg-white hover:bg-navy-50 text-navy-900 border-2 border-navy-200 rounded-xl transition-all"
          >
            <ArrowLeft className="w-5 h-5" />
            <span>다른 기사 분석하기</span>
          </button>
        </motion.div>
      </main>

      {/* Preview Modal */}
      {showPreviewModal && (
        <TxtPreviewModal
          result={result}
          onClose={() => setShowPreviewModal(false)}
        />
      )}
    </div>
  );
}