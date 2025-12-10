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
  '익명 취재원은 불가피한 경우에만 제한적으로 사용해야 합니다.',
  '언론윤리헌장은 "언론은 시민을 위해 존재하며..."로 시작합니다.',
  "사진과 영상은 조작하거나 맥락을 왜곡해서는 안 됩니다.",
  "통계 인용 시 출처와 조사 방법을 명시해야 합니다.",
  "보도자료를 그대로 옮겨 쓰는 것은 좋은 저널리즘이 아닙니다.",
  "좋은 기사는 최소 두 개 이상 독립적인 출처를 확인합니다.",
  "범죄 혐의자는 유죄 확정 전까지 '피의자'로 표현해야 합니다.",
  "성별, 외모, 출신 지역으로 사건을 설명하면 차별적 보도가 됩니다.",
  "따옴표 뒤에 숨지 말고 기자가 직접 사실을 검증해야 합니다.",
  '"~라는 지적"이 있다면, 누가 지적했는지 밝혀야 합니다.',
  "인용할 때 발언의 맥락을 왜곡하지 않아야 합니다.",
  "복잡한 사건은 배경과 맥락을 함께 제공해야 합니다.",
  "복잡한 사안을 지나치게 단순화하면 본질이 왜곡됩니다.",
  "취재원의 일방적인 주장을 검증 없이 받아쓰면 안 됩니다.",
  "취재원의 의도나 심리를 기자가 단정해서는 안 됩니다.",
  "여론조사 결과는 오차범위를 고려해 신중하게 해석해야 합니다.",
  "정보 출처가 불분명한 기사는 신뢰하기 어렵습니다.",
  "기자의 주관적인 판단이나 의견을 사실과 섞으면 안 됩니다.",
  "속보 경쟁에만 몰두하면 사실 확인이 소홀해집니다.",
  "성별, 연령, 지역으로 편견을 만들면 안 됩니다.",
  "장애·질병을 비하하는 차별적 표현을 쓰지 않습니다.",
  "특정 집단을 향한 혐오 표현이나 은어를 쓰지 않습니다.",
  "전문가 의견을 인용할 땐 그 사람의 전문 분야를 확인해야 합니다.",
  "보호가 필요한 익명 보도 시 신원이 추정될 정보를 흘리지 않습니다.",
  "시간적 순서만으로 인과관계를 단정해서는 안 됩니다.",
  "상관관계를 인과관계로 왜곡하지 않아야 합니다.",
  "일부 사례를 전체로 일반화해 보도해서는 안 됩니다.",
  "의혹 보도 시 반드시 당사자의 해명을 들어야 합니다.",
  "한쪽 주장만 듣고 기사를 쓰면 안 됩니다.",
  "논란이 있는 사안은 여러 관점을 함께 보도해야 합니다.",
  "한쪽 주장만 싣고 반대 의견을 생략하면 편향 보도입니다.",
  "갈등을 부추기는 과격한 표현을 쓰지 않습니다.",
  "갈등을 부추기는 전쟁 은유 표현을 남용하지 않습니다.",
  "논쟁적 사안은 다양한 관점을 균형 있게 다뤄야 합니다.",
  "오보가 발생하면 즉시 정정하고 사과해야 합니다.",
  "익명 사용 시 이유를 설명해야 합니다.",
  "현장 취재를 통해 생생한 목소리를 전달해야 합니다.",
  "SNS의 확인되지 않은 소문을 보도하지 않습니다.",
  "사건과 무관한 유명인의 가족을 언급하지 않습니다.",
  "공익과 무관한 개인의 사생활은 보도 대상이 아닙니다.",
  "해외 언론 기사 인용 시 원문을 확인해야 합니다.",
  "제목과 본문은 다른 이야기를 해서는 안 됩니다.",
  "정치적 대립 구도를 과장하는 제목은 피해야 합니다.",
  "자살 방법이나 장소를 구체적으로 묘사하지 않습니다.",
  "광고와 기사는 명확히 구분해야 합니다.",
  "온라인 기사는 수정 이력을 남기고 투명하게 고칩니다.",
  "진실과 거짓을 같은 비중으로 다루는 것은 공정 보도가 아닙니다.",
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
          // Increment 0.062 per 100ms => ~0.62% per second
          // Takes about 110 seconds to go from 30% to 98%
          if (prev < 98) {
            return prev + 0.062;
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
