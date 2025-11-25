import { motion, AnimatePresence } from 'framer-motion';
import { X, FileDown, FileText, Download } from 'lucide-react';
import type { AnalysisResult } from '../types';

interface TxtPreviewModalProps {
    result: AnalysisResult;
    onClose: () => void;
}

export function TxtPreviewModal({ result, onClose }: TxtPreviewModalProps) {
    const handleDownload = () => {
        const { article_info, reports } = result;
        const date = new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });

        let content = `
================================================================
  ____ ____       ____ _               _
 / ___|  _ \\     / ___| |__   ___  ___| | __
| |   | |_) |___| |   | '_ \\ / _ \\/ __| |/ /
| |___|  _ <|___| |___| | | |  __/ (__|   <
 \\____|_| \\_\\    \\____|_| |_|\\___|\\___|_|\\_\\

                  언론윤리 체크 도구
================================================================

[ 분석 개요 ]
• 생성 일시: ${date}
• 기사 제목: ${article_info.title}
• 기사 URL : ${article_info.url || '미확인'}
• 매체명   : ${article_info.publisher || '미확인'}
• 기자명   : ${article_info.journalist || '미확인'}
• 게재일시 : ${article_info.publishDate || '미확인'}
• 기사 유형: ${article_info.articleType || '미확인'}
• 기사 요소: ${article_info.articleElements || '미확인'}
• 편집 구조: ${article_info.editStructure || '미확인'}
• 취재 방식: ${article_info.reportingMethod || '미확인'}
• 내용 흐름: ${article_info.contentFlow || '미확인'}

================================================================
`;

        // Helper to add report section
        const addReport = (title: string, body: string) => {
            content += `
----------------------------------------------------------------
  ${title}
----------------------------------------------------------------

${body.trim()}

`;
        };

        addReport('시민을 위한 종합 리포트', reports.comprehensive);
        addReport('기자를 위한 전문 리포트', reports.journalist);
        addReport('학생을 위한 교육 리포트', reports.student);

        content += `
================================================================
  CR-Check: AI 기반 언론윤리 분석 리포트
================================================================

※ 활용 가이드: 이 리포트는 뉴스를 비판적으로 읽을 수 있게 돕는 '보조 도구'입니다. AI는 기사의 보도 관행 패턴을 감지해 연계되는 윤리규범과 함께 보여줄 뿐, 이를 확정적 판단의 근거로 삼을 수는 없습니다. 리포트의 내용을 무조건 신뢰하기보다, 기사 원문과 비교하며 직접 판단하고 토론하는 자료로 활용해 주시기 바랍니다.
`;

        const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `CR-Check_Report_${Date.now()}.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        onClose();
    };

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden"
                >
                    {/* Header */}
                    <div className="flex items-center justify-between p-6 border-b border-navy-100 bg-white">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-amber-100 rounded-lg">
                                <FileText className="w-6 h-6 text-amber-600" />
                            </div>
                            <div>
                                <h2 className="text-xl font-bold text-navy-900">리포트 내보내기</h2>
                                <p className="text-sm text-navy-600">분석 결과를 다운로드할 수 있습니다</p>
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-navy-50 rounded-full transition-colors"
                        >
                            <X className="w-6 h-6 text-navy-400" />
                        </button>
                    </div>

                    {/* Preview Content */}
                    <div className="flex-1 overflow-y-auto p-8 bg-navy-50/50 custom-scrollbar">
                        <div className="bg-white shadow-sm border border-navy-100 rounded-xl p-8 max-w-3xl mx-auto">
                            <div className="text-center mb-8 border-b-2 border-navy-900 pb-6">
                                <h1 className="text-2xl font-serif font-bold text-navy-900 mb-2">CR-Check</h1>
                                <p className="text-navy-600">기사 분석 리포트</p>
                            </div>

                            <div className="space-y-8">
                                {/* Article Info */}
                                <section>
                                    <h3 className="flex items-center gap-2 text-lg font-bold text-navy-900 mb-4 pb-2 border-b border-navy-100">
                                        <FileText className="w-5 h-5" />
                                        기사 정보
                                    </h3>
                                    <div className="space-y-3 text-sm text-navy-800">
                                        <p><strong className="text-navy-900">기사 제목:</strong> {result.article_info.title}</p>
                                        <p><strong className="text-navy-900">매체명:</strong> {result.article_info.publisher}</p>
                                        <p><strong className="text-navy-900">게재일시:</strong> {result.article_info.publishDate}</p>
                                        <p><strong className="text-navy-900">기자명:</strong> {result.article_info.journalist}</p>
                                        <p><strong className="text-navy-900">기사 유형:</strong> {result.article_info.articleType}</p>
                                        <p><strong className="text-navy-900">기사 요소:</strong> {result.article_info.articleElements}</p>
                                        <p><strong className="text-navy-900">편집 구조:</strong> {result.article_info.editStructure}</p>
                                        <p><strong className="text-navy-900">취재 방식:</strong> {result.article_info.reportingMethod}</p>
                                        <p><strong className="text-navy-900">내용 흐름:</strong> {result.article_info.contentFlow}</p>
                                    </div>
                                </section>

                                {/* Comprehensive Report Preview */}
                                <section>
                                    <h3 className="flex items-center gap-2 text-lg font-bold text-navy-900 mb-4 pb-2 border-b border-navy-100">
                                        <Users className="w-5 h-5" />
                                        시민을 위한 종합 리포트
                                    </h3>
                                    <div className="prose prose-sm max-w-none text-navy-700">
                                        <p className="whitespace-pre-wrap line-clamp-[10] text-ellipsis">
                                            {result.reports.comprehensive}
                                        </p>
                                        <p className="text-center text-navy-400 text-xs mt-4 italic">
                                            (전체 내용은 다운로드된 파일에서 확인하실 수 있습니다)
                                        </p>
                                    </div>
                                </section>
                            </div>
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="p-6 border-t border-navy-100 bg-white flex flex-col items-center gap-4">
                        <div className="flex w-full max-w-md gap-3">
                            <button
                                onClick={handleDownload}
                                className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-navy-900 hover:bg-navy-800 text-white rounded-xl transition-all font-medium shadow-lg shadow-navy-900/20"
                            >
                                <Download className="w-5 h-5" />
                                다운로드 시작
                            </button>
                            <button
                                onClick={onClose}
                                className="px-6 py-3 bg-white hover:bg-navy-50 text-navy-600 border border-navy-200 rounded-xl transition-all font-medium"
                            >
                                취소
                            </button>
                        </div>
                        <p className="text-xs text-navy-400">
                            * 리포트는 텍스트 파일(.txt) 형식으로 다운로드됩니다
                        </p>
                    </div>
                </motion.div>
            </div>
        </AnimatePresence>
    );
}

function Users(props: any) {
    return (
        <svg
            {...props}
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
            <circle cx="9" cy="7" r="4" />
            <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
            <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
    );
}
