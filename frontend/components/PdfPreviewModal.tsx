import { motion } from 'motion/react';
import { X, Download, FileText, Newspaper, Users, NotebookPen, BookOpenCheck } from 'lucide-react';
import type { AnalysisResult } from '../types';

interface PdfPreviewModalProps {
  result: AnalysisResult;
  onClose: () => void;
}

export function PdfPreviewModal({ result, onClose }: PdfPreviewModalProps) {
  const handleDownload = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/export-pdf`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(result),
      });

      if (!response.ok) {
        throw new Error("PDF 생성에 실패했습니다.");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `CR-Check_분석리포트_${result.article_info.title.slice(0, 20)}_${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Download failed:", error);
      alert("PDF 다운로드 중 오류가 발생했습니다.");
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-6"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
        className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-navy-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
              <FileText className="w-6 h-6 text-amber-700" />
            </div>
            <div>
              <h3 className="text-navy-900">리포트 내보내기</h3>
              <p className="text-navy-600 text-sm">분석 결과를 다운로드할 수 있습니다</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-10 h-10 flex items-center justify-center rounded-lg hover:bg-navy-50 transition-colors"
          >
            <X className="w-6 h-6 text-navy-600" />
          </button>
        </div>

        {/* Preview */}
        <div className="flex-1 overflow-auto p-6 bg-navy-50 custom-scrollbar">
          <div className="bg-white rounded-lg shadow-sm p-8 mx-auto max-w-3xl" style={{ aspectRatio: '210/297' }}>
            {/* Document Header */}
            <div className="text-center mb-8 pb-6 border-b-2 border-navy-900">
              <h1 className="text-navy-900 mb-2">CR-Check</h1>
              <p className="text-navy-600 text-sm">기사 분석 리포트</p>
            </div>

            {/* Article Info */}
            <div className="mb-8">
              <div className="flex items-center gap-2 mb-3 pb-2 border-b border-navy-200">
                <Newspaper className="w-4 h-4 text-navy-900" />
                <h4 className="text-navy-900">기사 정보</h4>
              </div>
              <div className="space-y-2 text-sm">
                <p className="text-navy-700">
                  <strong className="text-navy-900">기사 제목:</strong> {result.article_info.title}
                </p>
                <p className="text-navy-700">
                  <strong className="text-navy-900">매체명:</strong> {result.article_info.publisher || '미확인'}
                </p>
                <p className="text-navy-700">
                  <strong className="text-navy-900">게재일시:</strong> {result.article_info.publishDate || '미확인'}
                </p>
                <p className="text-navy-700">
                  <strong className="text-navy-900">기자명:</strong> {result.article_info.journalist || '미확인'}
                </p>
                <p className="text-navy-700">
                  <strong className="text-navy-900">기사 유형:</strong> {result.article_info.articleType || '일반 기사'}
                </p>
                <p className="text-navy-700">
                  <strong className="text-navy-900">기사 요소:</strong> {result.article_info.articleElements || '-'}
                </p>
                <p className="text-navy-700">
                  <strong className="text-navy-900">편집 구조:</strong> {result.article_info.editStructure || '-'}
                </p>
                <p className="text-navy-700">
                  <strong className="text-navy-900">취재 방식:</strong> {result.article_info.reportingMethod || '-'}
                </p>
                <p className="text-navy-700">
                  <strong className="text-navy-900">내용 흐름:</strong> {result.article_info.contentFlow || '-'}
                </p>
              </div>
            </div>

            {/* Reports Preview */}
            <div className="space-y-6">
              <div>
                <div className="flex items-center gap-2 mb-2 pb-2 border-b border-navy-200">
                  <Users className="w-4 h-4 text-navy-900" />
                  <h4 className="text-navy-900">시민을 위한 종합 리포트</h4>
                </div>
                <p className="text-navy-600 text-sm line-clamp-3">
                  {result.reports.comprehensive.substring(0, 200)}...
                </p>
              </div>

              <div>
                <div className="flex items-center gap-2 mb-2 pb-2 border-b border-navy-200">
                  <NotebookPen className="w-4 h-4 text-navy-900" />
                  <h4 className="text-navy-900">기자를 위한 전문 리포트</h4>
                </div>
                <p className="text-navy-600 text-sm line-clamp-3">
                  {result.reports.journalist.substring(0, 200)}...
                </p>
              </div>

              <div>
                <div className="flex items-center gap-2 mb-2 pb-2 border-b border-navy-200">
                  <BookOpenCheck className="w-4 h-4 text-navy-900" />
                  <h4 className="text-navy-900">학생을 위한 교육 리포트</h4>
                </div>
                <p className="text-navy-600 text-sm line-clamp-3">
                  {result.reports.student.substring(0, 200)}...
                </p>
              </div>
            </div>

            {/* Footer */}
            <div className="mt-8 pt-6 border-t border-navy-200">
              <div className="border-b border-navy-100 pb-4 mb-4">
                <p className="text-navy-600 text-xs leading-relaxed">
                  <strong>※ 활용 가이드:</strong> 이 리포트는 뉴스를 비판적으로 읽을 수 있게 돕는 '보조 도구'입니다. AI는 기사의 보도 관행 패턴을 감지해 연계되는 윤리규범과 함께 보여줄 뿐, 이를 확정적 판단의 근거로 삼을 수는 없습니다. 리포트의 내용을 무조건 신뢰하기보다, 기사 원문과 비교하며 직접 판단하고 토론하는 자료로 활용해 주시기 바랍니다.
                </p>
              </div>
              <p className="text-navy-400 text-xs">
                분석 일시: {new Date().toLocaleString('ko-KR')}
              </p>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="p-6 border-t border-navy-100 bg-navy-50">
          <div className="flex gap-4">
            <button
              onClick={handleDownload}
              className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-navy-900 hover:bg-navy-800 text-white rounded-xl transition-all"
            >
              <Download className="w-5 h-5" />
              <span>다운로드 시작</span>
            </button>
            <button
              onClick={onClose}
              className="px-6 py-3 bg-white hover:bg-navy-50 text-navy-900 border-2 border-navy-200 rounded-xl transition-all"
            >
              취소
            </button>
          </div>
          <p className="text-navy-500 text-xs text-center mt-4">
            * 리포트는 텍스트 파일(.txt) 형식으로 다운로드됩니다
          </p>
        </div>
      </motion.div>
    </motion.div>
  );
}