import { create } from 'zustand';

export const useAuthStore = create((set) => ({
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  token: localStorage.getItem('auth_token'),
  setAuth: (user, token) => {
    localStorage.setItem('user', JSON.stringify(user));
    localStorage.setItem('auth_token', token);
    set({ user, token });
  },
  logout: () => {
    localStorage.removeItem('user');
    localStorage.removeItem('auth_token');
    set({ user: null, token: null });
  },
}));

export const useMatchStore = create((set) => ({
  currentMatch: null,
  currentQuestion: 0,
  timeRemaining: 10,
  myScore: 0,
  opponentScore: 0,
  selectedAnswer: null,
  isLocked: false,
  setMatch: (match) => set({ currentMatch: match }),
  setQuestion: (index) => set({ currentQuestion: index }),
  setTime: (time) => set({ timeRemaining: time }),
  selectAnswer: (answer) => set({ selectedAnswer: answer, isLocked: true }),
  updateScores: (myScore, opponentScore) => set({ myScore, opponentScore }),
  reset: () => set({
    currentMatch: null,
    currentQuestion: 0,
    timeRemaining: 10,
    myScore: 0,
    opponentScore: 0,
    selectedAnswer: null,
    isLocked: false
  }),
}));
