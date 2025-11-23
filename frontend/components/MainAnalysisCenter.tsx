import { useState } from 'react';
import { Link2, BarChart3, Users, Scale } from 'lucide-react';
import type { ArticleInput } from '../types';

interface MainAnalysisCenterProps {
  onAnalyze: (input: ArticleInput) => void;
}

export function MainAnalysisCenter({ onAnalyze }: MainAnalysisCenterProps) {
  const [content, setContent] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (content.trim()) {
      onAnalyze({ type: 'url', content: content.trim() });
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-navy-50 via-white to-amber-50">
      {/* Header */}
      <header className="border-b border-navy-200 bg-white/80 backdrop-blur-sm">
        <div className="mx-auto max-w-7xl px-6 py-6">
          <div className="flex items-center justify-between">
            {/* Header content removed */}
          </div>
        </div>
      </header>

      {/* Main Section */}
      <main className="mx-auto max-w-4xl px-6 py-16">
        <div className="text-center mb-12">
          <p className="text-navy-600 text-lg text-[24px]">
            언론윤리 체크 도구 <span style={{ fontSize: '0.8em', opacity: 0.8 }}><span style={{ fontSize: '0.6em' }}>_</span>CR</span>
          </p>
        </div>

        {/* Input Card */}
        <div className="bg-white rounded-2xl shadow-xl border border-navy-100 overflow-hidden">
          {/* Input Form */}
          <form onSubmit={handleSubmit} className="p-8">
            <div className="mb-6">
              <div className="flex items-center gap-2 mb-3">
                <Link2 className="w-5 h-5 text-navy-600" />
                <label className="text-navy-700 text-lg">
                  <span className="md:hidden">기사의 URL을 입력해 주세요.</span>
                  <span className="hidden md:inline">분석하려는 뉴스 기사의 URL을 입력해 주세요.</span>
                </label>
              </div>
              <input
                type="text"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="뉴스 기사의 URL을 입력해 주세요..."
                className="w-full px-6 py-4 border-2 border-navy-200 rounded-xl focus:border-navy-500 focus:outline-none focus:ring-4 focus:ring-navy-100 transition-all text-sm placeholder:text-navy-500"
              />
            </div>

            <button
              type="submit"
              disabled={!content.trim()}
              className="w-full bg-navy-900 hover:bg-navy-800 disabled:bg-navy-300 disabled:cursor-not-allowed text-white py-5 rounded-xl transition-all transform hover:scale-[1.02] active:scale-[0.98]"
            >
              기사 분석 시작
            </button>

            <p className="text-navy-500 text-sm text-center mt-6">
              CR은 스트레이트 뉴스와 해설 기사 분석에 최적화되어 있습니다. (사설/칼럼, 리뷰 기사 등 제외)
            </p>
          </form>
        </div>

        {/* Info Cards */}
        <div className="grid md:grid-cols-3 gap-6 mt-12">
          <div className="bg-white/60 backdrop-blur-sm rounded-xl p-6 border border-navy-100">
            <div className="flex md:flex-col gap-3 md:gap-0 items-center md:items-start">
              <div className="w-12 h-12 bg-navy-100 rounded-lg flex items-center justify-center md:mb-4 shrink-0">
                <BarChart3 className="w-6 h-6 text-navy-700" />
              </div>
              <h3 className="text-navy-900 md:mb-2 text-xl md:text-base">정성적 평가</h3>
            </div>
            <p className="text-navy-600 text-sm mt-3 md:mt-0">
              등급이나 점수가 아닌, 기사의 맥락과 배경을 분석해 해설합니다.
            </p>
          </div>

          <div className="bg-white/60 backdrop-blur-sm rounded-xl p-6 border border-navy-100">
            <div className="flex md:flex-col gap-3 md:gap-0 items-center md:items-start">
              <div className="w-12 h-12 bg-amber-100 rounded-lg flex items-center justify-center md:mb-4 shrink-0">
                <Users className="w-6 h-6 text-amber-700" />
              </div>
              <h3 className="text-navy-900 md:mb-2 text-xl md:text-base">세 가지 관점</h3>
            </div>
            <p className="text-navy-600 text-sm mt-3 md:mt-0">
              시민을 위한 종합리포트, 기자와 학생을 위한 맞춤형 리포트를 제공합니다.
            </p>
          </div>

          <div className="bg-white/60 backdrop-blur-sm rounded-xl p-6 border border-navy-100">
            <div className="flex md:flex-col gap-3 md:gap-0 items-center md:items-start">
              <div className="w-12 h-12 bg-navy-100 rounded-lg flex items-center justify-center md:mb-4 shrink-0">
                <Scale className="w-6 h-6 text-navy-700" />
              </div>
              <h3 className="text-navy-900 md:mb-2 text-xl md:text-base">윤리규범 기반</h3>
            </div>
            <p className="text-navy-600 text-sm mt-3 md:mt-0">
              한국기자협회 언론윤리규범을 근거로 객관적이고 공정하게 분석합니다.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}