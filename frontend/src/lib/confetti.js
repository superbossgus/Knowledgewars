import confetti from 'canvas-confetti';

export const fireConfetti = (opts = {}) => {
  confetti({
    particleCount: 160,
    spread: 70,
    origin: { y: 0.6 },
    ...opts,
  });
};
