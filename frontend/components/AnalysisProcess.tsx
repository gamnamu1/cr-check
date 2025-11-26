"use client";

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileSearch, ClipboardCheck, CheckCircle2 } from 'lucide-react';
import type { AnalysisPhase } from '../types';

interface AnalysisProcessProps {
  isLoading: boolean;
  onComplete: () => void;
}

const ethicsTips = [
  "익명 취재원은 불가피한 경우에만 제한적으로 사용해야 합니다.",
  "기사 제목은 내용을 과장하거나 왜곡해서는 안 됩니다.",
  '언론윤리헌장 첫 문장은 "언론은 시민을 위해 존재하며..."로 시작합니다.',
  "사진과 영상은 조작하거나 맥락을 왜곡해서는 안 됩니다.",
  "통계 인용 시 출처와 조사 방법을 명시해야 합니다.",
  "보도자료를 그대로 옮겨 쓰는 것은 좋은 저널리즘이 아닙니다.",
  "좋은 기사는 최소 두 개 이상의 독립적인 출처를 확인합니다.",
  "비판 대상에게 충분한 해명 기회를 제공해야 합니다.",
  "따옴표 저널리즘: '누군가 말했다'가 진실을 담보하지 않습니다.",
  "범죄 혐의자는 유죄 확정 전까지 '혐의자' 또는 '피의자'로 표현해야 합니다.",
  '"~라는 비판이 나온다"에서 비판 주체가 없다면, 이는 기자의 생각일 수 있습니다.',
  "온라인 커뮤니티 글을 인용할 땐 대표성을 확인해야 합니다.",
  "상관관계와 인과관계는 다릅니다.",
  "성별, 외모, 출신 지역으로 사건을 설명하면 차별적 보도가 됩니다.",
  '"~라는 지적이다", "~라는 우려가 나온다"에서 지적·우려 주체를 찾아봅니다.',
  '"왜 이 시점에, 왜 이 매체에서 이 기사가 나왔을까?" 배경을 생각합니다.',
  "선택적 사실 보도: 일부 사실만 보도하여 전체 맥락을 왜곡해서는 안 됩니다.",
];

export function AnalysisProcess({ isLoading, onComplete }: AnalysisProcessProps) {
  const [phase, setPhase] = useState<AnalysisPhase>('scanning');
  const [currentTip, setCurrentTip] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // Initial scanning phase
    const scanningTimer = setTimeout(() => {
      setPhase('analyzing');
    }, 2000);

    return () => clearTimeout(scanningTimer);
  }, []);

  useEffect(() => {
    if (phase === 'analyzing' && !isLoading) {
      setPhase('complete');
      setTimeout(() => {
        onComplete();
      }, 2000);
    }
  }, [phase, isLoading, onComplete]);

  useEffect(() => {
    // Initial random tip
    setCurrentTip(Math.floor(Math.random() * ethicsTips.length));

    // Progress bar simulation
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        if (phase === 'complete') return 100;
        if (phase === 'scanning') {
          // 0 -> 30% in 2s (20 steps of 100ms)
          return Math.min(prev + 1.5, 30);
        }
        if (phase === 'analyzing') {
          // 30 -> 98% linear approach (steady pace)
          // Increment 0.07 per 100ms => ~0.7% per second
          // Takes about 97 seconds to go from 30% to 98%
          if (prev < 98) {
            return prev + 0.07;
          }
          return prev;
        }
        return prev;
      });
    }, 100);

    // Tips rotation (Random)
    const tipInterval = setInterval(() => {
      setCurrentTip((prev) => {
        let next;
        do {
          next = Math.floor(Math.random() * ethicsTips.length);
        } while (next === prev && ethicsTips.length > 1);
        return next;
      });
    }, 6000);

    return () => {
      clearInterval(progressInterval);
      clearInterval(tipInterval);
    };
  }, [phase]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-navy-50 via-white to-amber-50 flex items-center justify-center px-6">
      <div className="max-w-2xl w-full">
        <div className="bg-white rounded-2xl shadow-2xl border border-navy-100 p-12">
          {/* Logo */}
          <div className="text-center mb-8">
            <h2 className="text-navy-900 mb-2">CR-Check</h2>
            <p className="text-navy-600">분석이 진행되고 있습니다</p>
          </div>

          {/* Phase Animation */}
          <div className="mb-12">
            <AnimatePresence mode="wait">
              {phase === 'scanning' && (
                <motion.div
                  key="scanning"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="text-center"
                >
                  <motion.div
                    animate={{ scale: [1, 1.1, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                    className="inline-flex items-center justify-center w-24 h-24 bg-navy-100 rounded-full mb-6"
                  >
                    <FileSearch className="w-12 h-12 text-navy-700" />
                  </motion.div>
                  <h3 className="text-navy-900 mb-2 text-[24px]">1단계: 기사 구조 스캔 중</h3>
                </motion.div>
              )}

              {phase === 'analyzing' && (
                <motion.div
                  key="analyzing"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="text-center"
                >
                  <motion.div
                    animate={{ scale: [1, 1.1, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                    className="inline-flex items-center justify-center w-24 h-24 bg-amber-100 rounded-full mb-6"
                  >
                    <ClipboardCheck className="w-12 h-12 text-amber-700" />
                  </motion.div>
                  <h3 className="text-navy-900 mb-2 text-[24px]">2단계: 규범 대조 중</h3>
                  <p className="text-navy-600">
                    언론윤리규범 대조 및 리포트 작성 중...
                  </p>
                </motion.div>
              )}

              {phase === 'complete' && (
                <motion.div
                  key="complete"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="text-center"
                >
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", stiffness: 200, damping: 15 }}
                    className="inline-flex items-center justify-center w-24 h-24 bg-green-100 rounded-full mb-6"
                  >
                    <CheckCircle2 className="w-12 h-12 text-green-700" />
                  </motion.div>
                  <h3 className="text-navy-900 mb-2 text-[24px]">분석 완료!</h3>
                  <p className="text-navy-600">
                    결과 리포트를 불러오는 중입니다...
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Progress Bar */}
          <div className="mb-8">
            <div className="h-2 bg-navy-100 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-navy-600 to-amber-500"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>
            <p className="text-navy-500 text-sm text-center mt-2">
              {Math.round(progress)}% 완료
            </p>
          </div>

          {/* Document Scanning Animation */}
          <div className="mb-8 h-32 bg-navy-50 rounded-lg p-4 relative overflow-hidden">
            <motion.div
              className="absolute inset-0 bg-gradient-to-r from-transparent via-amber-200/30 to-transparent"
              animate={{ x: ['-100%', '200%'] }}
              transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            />
            <div className="space-y-2 relative">
              {[...Array(5)].map((_, i) => (
                <motion.div
                  key={i}
                  className="h-2 bg-navy-200 rounded"
                  style={{ width: `${80 - i * 10}%` }}
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.2 }}
                />
              ))}
            </div>
          </div>

          {/* Ethics Tip */}
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
            <p className="text-amber-900 text-sm mb-1">💡 저널리즘 윤리 상식</p>
            <AnimatePresence mode="wait">
              <motion.p
                key={currentTip}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="text-navy-700"
              >
                {ethicsTips[currentTip]}
              </motion.p>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
