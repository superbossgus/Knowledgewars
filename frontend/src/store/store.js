import { create } from 'zustand';
import { ESTADO_AUTH } from '../lib/authHydration.mjs';

const tokenGuardado = localStorage.getItem('auth_token');

export const useAuthStore = create((set) => ({
  // `user` sigue saliendo de `localStorage` para que el primer render tenga
  // algo que pintar, pero **ya no es la fuente de verdad**: mientras
  // `estadoAuth` no sea VERIFICADA ninguna ruta protegida lo mira. Ese era el
  // defecto H1 -- se decidia el muro de reaceptacion con un valor que nadie
  // habia confrontado con el servidor (BOS-596, §4 de `spec-h1`).
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  token: tokenGuardado,
  // Con token hay que hidratar antes de decidir nada; sin token no hay sesion
  // que verificar y `ProtectedRoute` manda a `/login` como siempre.
  estadoAuth: tokenGuardado ? ESTADO_AUTH.HIDRATANDO : ESTADO_AUTH.SIN_SESION,
  setEstadoAuth: (estadoAuth) => set({ estadoAuth }),
  setAuth: (user, token) => {
    localStorage.setItem('user', JSON.stringify(user));
    localStorage.setItem('auth_token', token);
    // Quien llama a `setAuth` acaba de hablar con el servidor -- el alta, el
    // ingreso, la reaceptacion o la propia hidratacion -- asi que la sesion
    // queda verificada.
    set({ user, token, estadoAuth: ESTADO_AUTH.VERIFICADA });
  },
  logout: () => {
    localStorage.removeItem('user');
    localStorage.removeItem('auth_token');
    set({ user: null, token: null, estadoAuth: ESTADO_AUTH.SIN_SESION });
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
