import React, { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import api from '../api/axios';

const quizStyles = `
  .quiz-modal-overlay {
    position: fixed; inset: 0; z-index: 9999;
    display: flex; align-items: center; justify-content: center;
    background: rgba(0,0,0,0.85); backdrop-filter: blur(8px);
    font-family: inherit;
  }
  .quiz-modal-content {
    background: #1f2937; color: #f9fafb; width: 100%; max-width: 650px;
    border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.6);
    display: flex; flex-direction: column; position: relative;
    border: 1px solid #374151; min-height: 450px; margin: 16px;
    animation: quizFadeIn 0.3s ease;
  }
  @keyframes quizFadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
  .quiz-close-btn {
    position: absolute; top: 16px; right: 16px; background: rgba(0,0,0,0.3); border: none;
    color: #9ca3af; cursor: pointer; padding: 8px; border-radius: 50%;
    transition: all 0.2s; display: flex; align-items: center; justify-content: center;
  }
  .quiz-close-btn:hover { background: rgba(0,0,0,0.6); color: #fff; }
  .quiz-header { text-align: center; padding: 24px 24px 12px; }
  .quiz-badge {
    background: rgba(37, 99, 235, 0.2); color: #60a5fa; padding: 6px 16px;
    border-radius: 9999px; font-size: 0.85rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.05em; border: 1px solid rgba(59, 130, 246, 0.3); display: inline-block;
  }
  .quiz-body { padding: 16px 32px 32px; flex: 1; display: flex; flex-direction: column; }
  .quiz-question { font-size: 1.5rem; font-weight: 700; line-height: 1.4; margin-bottom: 32px; text-align: center; color: #f3f4f6; }
  .quiz-options { display: flex; flex-direction: column; gap: 12px; width: 100%; }
  .quiz-option-btn {
    display: flex; align-items: center; gap: 16px; width: 100%; padding: 16px 20px;
    border-radius: 12px; border: 2px solid transparent; background: #374151;
    color: #e5e7eb; cursor: pointer; transition: all 0.2s; text-align: left; font-size: 1.1rem;
  }
  .quiz-option-btn:not(:disabled):hover { background: #4b5563; border-color: #6b7280; }
  .quiz-option-letter {
    display: flex; align-items: center; justify-content: center; width: 36px; height: 36px;
    border-radius: 8px; background: #111827; border: 1px solid #4b5563;
    font-weight: bold; font-size: 0.9rem; flex-shrink: 0; color: #9ca3af;
  }
  .quiz-option-btn.selected { background: rgba(37, 99, 235, 0.2); border-color: #3b82f6; color: #bfdbfe; }
  .quiz-option-btn.selected .quiz-option-letter { background: rgba(59, 130, 246, 0.3); border-color: #60a5fa; color: #93c5fd; }
  
  .quiz-option-btn.correct { background: rgba(22, 163, 74, 0.2); border-color: #22c55e; color: #dcfce3; }
  .quiz-option-btn.correct .quiz-option-letter { background: rgba(34, 197, 94, 0.3); border-color: #4ade80; color: #bbf7d0; }
  
  .quiz-option-btn.wrong { background: rgba(220, 38, 38, 0.2); border-color: rgba(239, 68, 68, 0.6); color: #fecaca; }
  .quiz-option-btn.wrong .quiz-option-letter { background: rgba(239, 68, 68, 0.3); border-color: #f87171; color: #fca5a5; }
  
  .quiz-option-btn.dimmed { opacity: 0.5; cursor: not-allowed; }
  
  .quiz-footer { margin-top: 32px; display: flex; justify-content: center; }
  .quiz-next-btn {
    background: #2563eb; color: #fff; padding: 14px 40px; border-radius: 9999px;
    font-size: 1.1rem; font-weight: 600; cursor: pointer; border: none; transition: background 0.2s;
  }
  .quiz-next-btn:hover { background: #1d4ed8; }
  .quiz-next-btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .quiz-result-card { text-align: center; padding: 40px; }
  .quiz-score-circle {
    width: 140px; height: 140px; border-radius: 50%; border: 8px solid #3b82f6;
    display: flex; align-items: center; justify-content: center; margin: 0 auto 24px;
    font-size: 2.5rem; font-weight: 800; color: #fff; box-shadow: 0 0 30px rgba(59,130,246,0.3);
  }
`;

export default function QuizModal({ userMessage, triggerReason, onClose, onComplete }) {
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [fetchError, setFetchError] = useState(false);

  useEffect(() => {
    let active = true;
    const fetchQuiz = async () => {
      try {
        setLoading(true);
        setFetchError(false);
        const res = await api.post('/quiz/generate', {
          message: userMessage,          // raw user text → backend extracts topic + count
          trigger_reason: triggerReason || 'direct_request'
        });
        if (active && res.data.success) {
          setQuiz(res.data.quiz);
        } else if (active) {
          setFetchError(true);
        }
      } catch (err) {
        console.error("Failed to generate quiz", err);
        if (active) setFetchError(true);
      } finally {
        if (active) setLoading(false);
      }
    };
    fetchQuiz();
    return () => { active = false; };
  }, [userMessage, triggerReason]);

  const handleOptionSelect = (questionId, optionLetter) => {
    if (answers[questionId]) return;
    setAnswers((prev) => ({ ...prev, [questionId]: optionLetter }));
  };

  const handleNext = async () => {
    if (currentIndex < (quiz?.questions?.length || 0) - 1) {
      setCurrentIndex((prev) => prev + 1);
    } else {
      try {
        setSubmitting(true);
        const res = await api.post('/quiz/submit', {
          quiz_id: quiz.quiz_id,
          answers: answers
        });
        if (res.data.success) {
          setQuiz(res.data.quiz);
        }
      } catch (err) {
        console.error("Submission failed", err);
      } finally {
        setSubmitting(false);
        setShowResult(true);
      }
    }
  };

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) onClose();
  };

  const currentQ = quiz?.questions?.[currentIndex];
  const answeredCurrent = currentQ ? !!answers[currentQ.question_id] : false;

  return createPortal(
    <>
      <style>{quizStyles}</style>
      <div className="quiz-modal-overlay" onClick={handleBackdropClick}>
        <div className="quiz-modal-content">
          {!showResult && (
            <button className="quiz-close-btn" onClick={onClose} aria-label="Close Quiz">
              <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}

          {loading ? (
             <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', padding: '40px', flex: 1 }}>
              <div style={{ width: '40px', height: '40px', border: '3px solid rgba(255,255,255,0.2)', borderTopColor: '#3b82f6', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
              <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
              <p style={{ marginTop: '20px', fontSize: '1.2rem', color: '#9ca3af' }}>Generating your tailored quiz...</p>
            </div>
          ) : fetchError || !quiz || !quiz.questions ? (
             <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', padding: '40px', flex: 1 }}>
                <p style={{ color: '#f87171', fontSize: '1.2rem', marginBottom: '20px' }}>Failed to load quiz. Please try again.</p>
                <button className="quiz-next-btn" onClick={onClose}>Close</button>
             </div>
          ) : showResult ? (
            <div className="quiz-result-card">
              <h2 style={{ fontSize: '2rem', marginBottom: '8px', color: '#fff', fontWeight: 'bold' }}>Quiz Completed!</h2>
              <p style={{ color: '#9ca3af', marginBottom: '32px' }}>Topic: {quiz.topic}</p>
              <div className="quiz-score-circle">
                {quiz.score?.percentage != null ? Math.round(quiz.score.percentage) + '%' : 'Done'}
              </div>
              <p style={{ fontSize: '1.2rem', color: '#e5e7eb', marginBottom: '40px' }}>
                {quiz.score?.correct != null ? 
                  `You answered ${quiz.score.correct} out of ${quiz.score.total} questions correctly.` :
                  'Your answers have been recorded.'}
              </p>
              <button 
                className="quiz-next-btn" 
                onClick={() => {
                  if (onComplete) onComplete(quiz, answers);
                  onClose();
                }}
              >
                Return to Chat
              </button>
            </div>
          ) : (
            <>
              <div className="quiz-header">
                <span className="quiz-badge">
                  Question {currentIndex + 1} of {quiz.total_questions || quiz.questions.length}
                </span>
              </div>
              <div className="quiz-body">
                <h3 className="quiz-question">{currentQ.question}</h3>
                
                <div className="quiz-options">
                  {currentQ.options.map((opt) => {
                    let optionLetter = opt.charAt(0);
                    let optionText = opt.substring(3);
                    
                    if (!['A','B','C','D'].includes(optionLetter)) {
                       const letters = ['A','B','C','D'];
                       const idx = currentQ.options.indexOf(opt);
                       optionLetter = letters[idx] || 'X';
                       optionText = opt;
                    }
                    
                    const isSelected = answers[currentQ.question_id] === optionLetter;
                    const isCorrect = currentQ.correct_answer === optionLetter;
                    
                    let btnClass = "quiz-option-btn";
                    if (answeredCurrent) {
                      if (isCorrect) btnClass += " correct";
                      else if (isSelected && !isCorrect) btnClass += " wrong";
                      else btnClass += " dimmed";
                    } else if (isSelected) {
                      btnClass += " selected";
                    }

                    return (
                      <button 
                        key={optionLetter}
                        onClick={() => handleOptionSelect(currentQ.question_id, optionLetter)}
                        disabled={answeredCurrent}
                        className={btnClass}
                      >
                        <span className="quiz-option-letter">{optionLetter}</span>
                        <span>{optionText}</span>
                      </button>
                    );
                  })}
                </div>

                {answeredCurrent && (
                  <div className="quiz-footer">
                    <button 
                      className="quiz-next-btn" 
                      onClick={handleNext}
                      disabled={submitting}
                    >
                      {submitting ? 'Submitting...' : (currentIndex < quiz.questions.length - 1 ? 'Next Question' : 'Finish Quiz')}
                    </button>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </>,
    document.body
  );
}