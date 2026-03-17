import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  es: {
    common: {
      app_name: 'Knowledge Wars',
      play: 'JUGAR',
      cancel: 'Cancelar',
      confirm: 'Confirmar',
      loading: 'Cargando...',
      error: 'Error',
      success: 'Éxito',
      close: 'Cerrar',
      welcome_back: 'Bienvenido de nuevo'
    },
    auth: {
      login: 'Iniciar Sesión',
      register: 'Registrarse',
      email: 'Correo Electrónico',
      password: 'Contraseña',
      display_name: 'Nombre de Usuario',
      country: 'País',
      favorite_topic: 'Tema Favorito',
      language: 'Idioma',
      logout: 'Cerrar Sesión'
    },
    home: {
      play_random: 'Jugar Aleatorio',
      play_random_desc: '¡Desafía a un oponente aleatorio y demuestra tus conocimientos!',
      top_topics: 'Temas Más Jugados',
      weekly_topic: 'Tema Semanal',
      duels_remaining: 'Duelos Restantes',
      games_remaining: 'Partidas',
      unlimited: 'Ilimitado',
      premium_status: 'Estado Premium',
      dnd_mode: 'No Molestar',
      store: 'Tienda',
      store_desc: '50 partidas por $99 MXN',
      go_to_store: 'Ir a la Tienda',
      buy_games: '¡Comprar Partidas!',
      low_games: '¡Pocas partidas! Comprar más',
      quick_actions: 'Acciones Rápidas',
      rankings: 'Rankings'
    },
    lobby: {
      back_home: 'Volver al Inicio',
      matchmaking: 'Buscar Oponente',
      find_opponent: '¡Encuentra un oponente y comienza a jugar!',
      select_topic: 'Seleccionar Tema',
      play_random: 'Jugar Partida Aleatoria',
      challenge_random: '¡Retar a un oponente aleatorio ahora!',
      online_players: 'Jugadores en Línea',
      no_online: 'No hay jugadores en línea ahora',
      challenge: 'Retar',
      no_users: 'No hay usuarios disponibles'
    },
    topics: {
      'General Knowledge': 'Conocimiento General',
      'Sports': 'Deportes',
      'History': 'Historia',
      'Science': 'Ciencia',
      'Technology': 'Tecnología',
      'Movies/TV': 'Películas/TV',
      'Music': 'Música',
      'Gaming': 'Videojuegos',
      'Geography': 'Geografía',
      'Business/Finance': 'Negocios/Finanzas'
    },
    match: {
      question: 'Pregunta',
      timer: 'Tiempo',
      score: 'Puntuación',
      request_hint: 'Pedir Pista',
      hint_penalty: '-1 punto',
      correct: '¡Correcto! +2 puntos',
      incorrect: 'Incorrecto',
      opponent_hint: 'Tu rival pidió una pista',
      waiting: 'Esperando jugadores...'
    },
    results: {
      victory: '¡Victoria!',
      defeat: 'Derrota',
      draw: 'Empate',
      elo_change: 'Cambio de ELO',
      rematch: 'Revancha',
      share: 'Compartir',
      back_home: 'Volver al Inicio'
    },
    rankings: {
      global: 'Global',
      weekly: 'Semanal',
      by_topic: 'Por Tema',
      rank: 'Rango',
      player: 'Jugador',
      elo: 'ELO',
      wins: 'Victorias',
      losses: 'Derrotas'
    },
    profile: {
      league: 'Liga',
      stats: 'Estadísticas',
      match_history: 'Historial',
      total_duels: 'Duelos Totales'
    },
    premium: {
      title: 'Knowledge Wars Premium',
      unlimited_duels: 'Duelos Ilimitados',
      no_ads: 'Sin Anuncios',
      special_themes: 'Temas Especiales',
      price_monthly: '$3.99/mes',
      subscribe: 'Suscribirse',
      buy_100: 'Comprar +100 Duelos',
      price_100: '$2.50 USD'
    }
  },
  en: {
    common: {
      app_name: 'Knowledge Wars',
      play: 'Play',
      cancel: 'Cancel',
      confirm: 'Confirm',
      loading: 'Loading...',
      error: 'Error',
      success: 'Success',
      close: 'Close'
    },
    auth: {
      login: 'Login',
      register: 'Register',
      email: 'Email',
      password: 'Password',
      display_name: 'Display Name',
      country: 'Country',
      favorite_topic: 'Favorite Topic',
      language: 'Language',
      logout: 'Logout'
    },
    home: {
      play_random: 'Play Random',
      top_topics: 'Top Topics',
      weekly_topic: 'Weekly Topic',
      duels_remaining: 'Duels Remaining',
      unlimited: 'Unlimited',
      premium_status: 'Premium Status',
      dnd_mode: 'Do Not Disturb'
    },
    match: {
      question: 'Question',
      timer: 'Time',
      score: 'Score',
      request_hint: 'Request Hint',
      hint_penalty: '-1 point',
      correct: 'Correct! +2 points',
      incorrect: 'Incorrect',
      opponent_hint: 'Your opponent requested a hint',
      waiting: 'Waiting for players...'
    },
    results: {
      victory: 'Victory!',
      defeat: 'Defeat',
      draw: 'Draw',
      elo_change: 'ELO Change',
      rematch: 'Rematch',
      share: 'Share',
      back_home: 'Back to Home'
    },
    rankings: {
      global: 'Global',
      weekly: 'Weekly',
      by_topic: 'By Topic',
      rank: 'Rank',
      player: 'Player',
      elo: 'ELO',
      wins: 'Wins',
      losses: 'Losses'
    },
    profile: {
      league: 'League',
      stats: 'Statistics',
      match_history: 'Match History',
      total_duels: 'Total Duels'
    },
    premium: {
      title: 'Knowledge Wars Premium',
      unlimited_duels: 'Unlimited Duels',
      no_ads: 'No Ads',
      special_themes: 'Special Themes',
      price_monthly: '$3.99/month',
      subscribe: 'Subscribe',
      buy_100: 'Buy +100 Duels',
      price_100: '$2.50 USD'
    }
  },
  pt: {
    common: {
      app_name: 'Knowledge Wars',
      play: 'Jogar',
      cancel: 'Cancelar',
      confirm: 'Confirmar',
      loading: 'Carregando...',
      error: 'Erro',
      success: 'Sucesso',
      close: 'Fechar'
    },
    auth: {
      login: 'Entrar',
      register: 'Registrar',
      email: 'E-mail',
      password: 'Senha',
      display_name: 'Nome de Usuário',
      country: 'País',
      favorite_topic: 'Tema Favorito',
      language: 'Idioma',
      logout: 'Sair'
    },
    home: {
      play_random: 'Jogar Aleatório',
      top_topics: 'Temas Mais Jogados',
      weekly_topic: 'Tema Semanal',
      duels_remaining: 'Duelos Restantes',
      unlimited: 'Ilimitado',
      premium_status: 'Status Premium',
      dnd_mode: 'Não Perturbe'
    },
    match: {
      question: 'Pergunta',
      timer: 'Tempo',
      score: 'Pontuação',
      request_hint: 'Pedir Dica',
      hint_penalty: '-1 ponto',
      correct: 'Correto! +2 pontos',
      incorrect: 'Incorreto',
      opponent_hint: 'Seu adversário pediu uma dica',
      waiting: 'Aguardando jogadores...'
    },
    results: {
      victory: 'Vitória!',
      defeat: 'Derrota',
      draw: 'Empate',
      elo_change: 'Mudança de ELO',
      rematch: 'Revanche',
      share: 'Compartilhar',
      back_home: 'Voltar ao Início'
    },
    rankings: {
      global: 'Global',
      weekly: 'Semanal',
      by_topic: 'Por Tema',
      rank: 'Classificação',
      player: 'Jogador',
      elo: 'ELO',
      wins: 'Vitórias',
      losses: 'Derrotas'
    },
    profile: {
      league: 'Liga',
      stats: 'Estatísticas',
      match_history: 'Histórico',
      total_duels: 'Duelos Totais'
    },
    premium: {
      title: 'Knowledge Wars Premium',
      unlimited_duels: 'Duelos Ilimitados',
      no_ads: 'Sem Anúncios',
      special_themes: 'Temas Especiais',
      price_monthly: '$3.99/mês',
      subscribe: 'Assinar',
      buy_100: 'Comprar +100 Duelos',
      price_100: '$2.50 USD'
    }
  }
};

i18n
  .use(initReactI18next)
  .init({
    resources: {
      es: { translation: resources.es },
      en: { translation: resources.en },
      pt: { translation: resources.pt }
    },
    lng: navigator.language.split('-')[0] || 'es',
    fallbackLng: 'es',
    defaultNS: 'translation',
    interpolation: {
      escapeValue: false
    }
  });

export default i18n;
