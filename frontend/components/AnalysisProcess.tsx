"use client";

import { useEffect, useState, useRef, ComponentType } from 'react';
import dynamic from 'next/dynamic';
import { FileSearch, ClipboardCheck, CheckCircle2 } from 'lucide-react';
import type { AnalysisPhase } from '../types';

interface AnalysisProcessProps {
  isLoading: boolean;
  onComplete: () => void;
}

import { ETHICS_TIPS } from '@/lib/constants/ethics-tips';

// Dynamic imports for Framer Motion
const MotionDiv = dynamic(
  () => import('framer-motion').then((mod) => mod.motion.div as ComponentType<any>),
  { ssr: false }
);

const MotionP = dynamic(
  () => import('framer-motion').then((mod) => mod.motion.p as ComponentType<any>),
  { ssr: false }
);

const AnimatePresence = dynamic(
  () => import('framer-motion').then((mod) => mod.AnimatePresence as ComponentType<any>),
  { ssr: false }
);

export function AnalysisProcess({ isLoading, onComplete }: AnalysisProcessProps) {
  const [phase, setPhase] = useState<AnalysisPhase>('scanning');
  const [currentTip, setCurrentTip] = useState(0);
  const [progress, setProgress] = useState(0);
  // Store the shuffled order of indices
  const [shuffledIndices, setShuffledIndices] = useState<number[]>([]);
  // Store the current position in the shuffled array
  const [currentIndex, setCurrentIndex] = useState(0);

  // Store onComplete in a ref to avoid dependency issues
  const onCompleteRef = useRef(onComplete);

  // Update ref when prop changes
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    // Initial scanning phase
    const scanningTimer = setTimeout(() => {
      setPhase('analyzing');
    }, 2000);

    // Shuffle the tips indices on mount
    const indices = Array.from({ length: ETHICS_TIPS.length }, (_, i) => i);
    for (let i = indices.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [indices[i], indices[j]] = [indices[j], indices[i]];
    }
    setShuffledIndices(indices);
    setCurrentTip(indices[0]); // Set initial tip

    return () => clearTimeout(scanningTimer);
  }, []);

  useEffect(() => {
    if (phase === 'analyzing' && !isLoading) {
      setPhase('complete');
      setTimeout(() => {
        onCompleteRef.current();
      }, 2000);
    }
  }, [phase, isLoading]); // onComplete removed from dependencies

  useEffect(() => {
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

    // Tips rotation (Sequential from shuffled list)
    const tipInterval = setInterval(() => {
      setCurrentIndex((prevIndex: number) => {
        const nextIndex = (prevIndex + 1) % ETHICS_TIPS.length;
        // If we wrapped around, we might want to reshuffle, but user just asked for "before one cycle ends", 
        // so simple wrapping is fine or we could reshuffle here. 
        // For 45 items at 6s each, one cycle is 270s (4.5 min). Analysis likely finishes before that.
        // So simple wrapping is sufficient.
        if (shuffledIndices.length > 0) {
          setCurrentTip(shuffledIndices[nextIndex]);
        }
        return nextIndex;
      });
    }, 6000);

    return () => {
      clearInterval(progressInterval);
      clearInterval(tipInterval);
    };
  }, [phase, shuffledIndices]);

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
                <MotionDiv
                  key="scanning"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="text-center"
                >
                  <MotionDiv
                    animate={{ scale: [1, 1.1, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                    className="inline-flex items-center justify-center w-24 h-24 bg-navy-100 rounded-full mb-6"
                  >
                    <FileSearch className="w-12 h-12 text-navy-700" />
                  </MotionDiv>
                  <h3 className="text-navy-900 mb-2 text-[24px]">1단계: 기사 구조 스캔 중</h3>
                </MotionDiv>
              )}

              {phase === 'analyzing' && (
                <MotionDiv
                  key="analyzing"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="text-center"
                >
                  <MotionDiv
                    animate={{ scale: [1, 1.1, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                    className="inline-flex items-center justify-center w-24 h-24 bg-amber-100 rounded-full mb-6"
                  >
                    <ClipboardCheck className="w-12 h-12 text-amber-700" />
                  </MotionDiv>
                  <h3 className="text-navy-900 mb-2 text-[24px]">2단계: 규범 대조 중</h3>
                  <p className="text-navy-600">
                    언론윤리규범 대조 및 리포트 작성 중...
                  </p>
                </MotionDiv>
              )}

              {phase === 'complete' && (
                <MotionDiv
                  key="complete"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="text-center"
                >
                  <MotionDiv
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", stiffness: 200, damping: 15 }}
                    className="inline-flex items-center justify-center w-24 h-24 bg-green-100 rounded-full mb-6"
                  >
                    <CheckCircle2 className="w-12 h-12 text-green-700" />
                  </MotionDiv>
                  <h3 className="text-navy-900 mb-2 text-[24px]">분석 완료!</h3>
                  <p className="text-navy-600">
                    결과 리포트를 불러오는 중입니다...
                  </p>
                </MotionDiv>
              )}
            </AnimatePresence>
          </div>

          {/* Progress Bar */}
          <div className="mb-8">
            <div className="h-2 bg-navy-100 rounded-full overflow-hidden">
              <MotionDiv
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
            <MotionDiv
              className="absolute inset-0 bg-gradient-to-r from-transparent via-amber-200/30 to-transparent"
              animate={{ x: ['-100%', '200%'] }}
              transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
            />
            <div className="space-y-2 relative">
              {[...Array(5)].map((_, i) => (
                <MotionDiv
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
              <MotionP
                key={currentTip}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="text-navy-700"
              >
                {ETHICS_TIPS[currentTip]}
              </MotionP>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
