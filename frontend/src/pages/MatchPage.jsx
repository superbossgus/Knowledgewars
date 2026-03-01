import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuthStore } from '../store/store';
import { TimerRing } from '../components/custom/TimerRing';
import { AnswerOption } from '../components/custom/AnswerOption';
import { ScoreBoard } from '../components/custom/ScoreBoard';
import api from '../lib/api';
import { toast } from 'sonner';
import { Lightbulb, AlertCircle } from 'lucide-react';

export default function MatchPage() {
  const { matchId } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { user } = useAuthStore();
  
  const [match, setMatch] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [timeRemaining, setTimeRemaining] = useState(10);
  const [myScore, setMyScore] = useState(0);
  const [opponentScore, setOpponentScore] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [answerState, setAnswerState] = useState('idle'); // idle, correct, wrong
  const [isLocked, setIsLocked] = useState(false);
  const [hintUsed, setHintUsed] = useState(false);
  const [hintText, setHintText] = useState('');
  const [showHintDialog, setShowHintDialog] = useState(false);
  
  const wsRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    loadMatch();
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [matchId]);

  const loadMatch = async () => {
    try {
      const response = await api.get(`/api/matches/${matchId}`);
      setMatch(response.data.match);
      setMyScore(response.data.match.score_a);
      setOpponentScore(response.data.match.score_b);
    } catch (error) {
      toast.error('Failed to load match');
      navigate('/home');
    }
  };

  const connectWebSocket = () => {
    const token = localStorage.getItem('auth_token');
    const wsUrl = process.env.REACT_APP_BACKEND_URL.replace('http', 'ws');
    const ws = new WebSocket(`${wsUrl}/ws/match/${matchId}?token=${token}`);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleWebSocketMessage(data);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
      console.log('WebSocket closed');
    };
    
    wsRef.current = ws;
  };

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'match_state':
        setMatch(data.match);
        startTimer();
        break;
      
      case 'answer_result':
        if (data.user_id === user.id) {
          if (data.result === 'correct') {
            setAnswerState('correct');
            setMyScore((prev) => prev + 2);
            toast.success(t('match.correct'));
            setTimeout(() => {
              nextQuestion();
            }, 2000);
          } else if (data.result === 'incorrect') {
            setAnswerState('wrong');
            setIsLocked(true);
            toast.error(t('match.incorrect'));
          }
        } else {
          if (data.result === 'correct') {
            setOpponentScore((prev) => prev + 2);
            setTimeout(() => {
              nextQuestion();
            }, 2000);
          }
        }
        break;
      
      case 'hint_result':
        if (data.result === 'success') {
          setHintText(data.hint);
          setHintUsed(true);
          setMyScore((prev) => prev - 1);
          toast.info(data.hint);
        }
        break;
      
      case 'opponent_hint':
        toast(t('match.opponent_hint'), { icon: <Lightbulb className="w-4 h-4" /> });
        break;
      
      case 'match_finished':
        navigate(`/results/${matchId}`, { state: { matchData: data } });
        break;
      
      default:
        break;
    }
  };

  const startTimer = () => {
    setTimeRemaining(10);
    if (timerRef.current) clearInterval(timerRef.current);
    
    timerRef.current = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(timerRef.current);
          nextQuestion();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const nextQuestion = () => {
    if (currentQuestion < 9) {
      setCurrentQuestion((prev) => prev + 1);
      setSelectedAnswer(null);
      setAnswerState('idle');
      setIsLocked(false);
      setHintUsed(false);
      setHintText('');
      startTimer();
    }
  };

  const handleAnswerSelect = (letter) => {
    if (isLocked || selectedAnswer) return;
    
    setSelectedAnswer(letter);
    setIsLocked(true);
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'submit_answer',
        question_index: currentQuestion,
        answer: letter
      }));
    }
  };

  const handleRequestHint = () => {
    setShowHintDialog(true);
  };

  const confirmHint = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'request_hint',
        question_index: currentQuestion
      }));
    }
    setShowHintDialog(false);
  };

  if (!match || !match.questions || match.questions.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p>{t('match.waiting')}</p>
        </div>
      </div>
    );
  }

  const question = match.questions[currentQuestion];
  const isPlayerA = match.player_a_id === user.id;

  return (
    <div className="min-h-screen p-4 md:p-6">
      <div className="container mx-auto max-w-4xl">
        {/* Header with Scoreboard and Timer */}
        <div className="sticky top-0 z-30 flex items-center justify-between gap-3 bg-gradient-to-b from-black/40 to-transparent p-3 backdrop-blur-md rounded-2xl mb-6">
          <ScoreBoard
            me={{
              name: isPlayerA ? match.player_a_name : match.player_b_name,
              flag: isPlayerA ? match.player_a_country : match.player_b_country,
              score: myScore
            }}
            opponent={{
              name: isPlayerA ? match.player_b_name : match.player_a_name,
              flag: isPlayerA ? match.player_b_country : match.player_a_country,
              score: opponentScore
            }}
          />
          <TimerRing seconds={timeRemaining} />
        </div>

        {/* Question */}
        <motion.div
          key={currentQuestion}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-6 mb-6"
        >
          <div className="text-sm text-muted-foreground mb-2">
            Question {currentQuestion + 1} / 10
          </div>
          <div className="text-lg md:text-xl font-medium" data-testid="match-question-text">
            {question.question}
          </div>
        </motion.div>

        {/* Answers Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-6">
          {['A', 'B', 'C', 'D', 'E', 'F'].map((letter) => (
            <AnswerOption
              key={letter}
              label={letter}
              text={question.options[letter]}
              state={selectedAnswer === letter ? answerState : 'idle'}
              onSelect={() => handleAnswerSelect(letter)}
              disabled={isLocked}
            />
          ))}
        </div>

        {/* Hint Button */}
        {!hintUsed && (
          <div className="flex items-center justify-between p-4 rounded-lg bg-card/50 border border-white/10">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Lightbulb className="w-4 h-4" />
              <span>Need help? Request a hint</span>
            </div>
            <button
              onClick={handleRequestHint}
              className="btn-secondary-glass px-4 py-2 text-sm"
              data-testid="request-hint-button"
            >
              Hint (-1 point)
            </button>
          </div>
        )}

        {hintText && (
          <div className="mt-3 p-4 rounded-lg bg-accent/10 border border-accent/30 flex items-start gap-3">
            <Lightbulb className="w-5 h-5 text-accent shrink-0 mt-0.5" />
            <div className="text-sm">{hintText}</div>
          </div>
        )}
      </div>

      {/* Hint Confirmation Dialog */}
      {showHintDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-card border border-white/10 rounded-2xl p-6 max-w-md w-full"
          >
            <div className="flex items-center gap-3 mb-4">
              <AlertCircle className="w-6 h-6 text-accent" />
              <h3 className="text-xl font-semibold">Request Hint?</h3>
            </div>
            <p className="text-muted-foreground mb-6">
              Requesting a hint will cost you <strong>-1 point</strong>. Your opponent will be notified.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowHintDialog(false)}
                className="flex-1 btn-secondary-glass py-3"
              >
                Cancel
              </button>
              <button
                onClick={confirmHint}
                className="flex-1 btn-primary py-3"
                data-testid="confirm-hint-button"
              >
                Confirm
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}
