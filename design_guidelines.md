{
  "brand": {
    "app_name": "Knowledge Wars",
    "attributes": ["competitiva", "moderna", "rápida", "precisa", "jugable", "social"],
    "tone": "energética y justa; hype sin ruido; gaming competitivo accesible"
  },
  "i18n": {
    "languages": ["es", "en", "pt"],
    "library": "react-i18next",
    "install": "npm i i18next react-i18next",
    "setup_hint": "Crea /app/frontend/src/i18n.js con namespaces: common, onboarding, match, results, rankings, profile, paywall. Usa keys cortas y semánticas."
  },
  "color_system": {
    "persona": "Oscuro por defecto con acentos vibrantes (aqua/teal + lima eléctrica + coral suave). Evitar combinaciones púrpura/rosa saturadas (ver regla de gradiente).",
    "tokens_hsl_for_tailwind_index.css": {
      "root_light": {
        "--background": "0 0% 100%",
        "--foreground": "210 10% 10%",
        "--card": "0 0% 100%",
        "--card-foreground": "210 10% 10%",
        "--popover": "0 0% 100%",
        "--popover-foreground": "210 10% 10%",
        "--primary": "173 85% 34%", 
        "--primary-foreground": "0 0% 98%",
        "--secondary": "200 8% 94%",
        "--secondary-foreground": "210 10% 15%",
        "--accent": "167 92% 38%", 
        "--accent-foreground": "0 0% 100%",
        "--muted": "210 12% 96%",
        "--muted-foreground": "210 8% 40%",
        "--destructive": "8 78% 54%",
        "--destructive-foreground": "0 0% 98%",
        "--border": "210 14% 90%",
        "--input": "210 14% 90%",
        "--ring": "173 85% 34%",
        "--chart-1": "173 80% 40%",
        "--chart-2": "96 74% 40%",
        "--chart-3": "12 86% 56%",
        "--chart-4": "197 100% 35%",
        "--chart-5": "45 92% 52%",
        "--radius": "0.8rem"
      },
      "dark": {
        "--background": "222 30% 8%",
        "--foreground": "0 0% 98%",
        "--card": "222 32% 10%",
        "--card-foreground": "0 0% 98%",
        "--popover": "222 32% 10%",
        "--popover-foreground": "0 0% 98%",
        "--primary": "173 85% 45%", 
        "--primary-foreground": "222 30% 8%",
        "--secondary": "222 22% 16%",
        "--secondary-foreground": "0 0% 98%",
        "--accent": "96 86% 56%", 
        "--accent-foreground": "222 30% 8%",
        "--muted": "222 20% 18%",
        "--muted-foreground": "210 6% 62%",
        "--destructive": "8 78% 54%",
        "--destructive-foreground": "0 0% 98%",
        "--border": "222 18% 22%",
        "--input": "222 18% 22%",
        "--ring": "173 85% 45%",
        "--chart-1": "173 80% 50%",
        "--chart-2": "96 74% 54%",
        "--chart-3": "12 86% 60%",
        "--chart-4": "197 100% 46%",
        "--chart-5": "45 92% 58%",
        "--radius": "0.8rem"
      },
      "league_palette": {
        "bronce": "28 65% 46%",
        "plata": "214 10% 76%",
        "oro": "45 92% 54%",
        "diamante": "173 85% 55%",
        "maestro": "197 100% 54%",
        "gran_maestro": "96 86% 56%"
      },
      "gradients": {
        "hero_soft": "linear-gradient(135deg, hsl(222 32% 10%) 0%, hsl(210 28% 12%) 40%, hsl(173 30% 12%) 100%)",
        "cta_glow": "linear-gradient(180deg, hsl(173 85% 48%) 0%, hsl(173 85% 42%) 100%)",
        "accent_strip": "linear-gradient(90deg, hsl(96 86% 56%) 0%, hsl(45 92% 58%) 100%)"
      },
      "textures": {
        "noise_css": ".noise-overlay{pointer-events:none;position:absolute;inset:0;background-image:url('data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'100%\' height=\'100%\'><filter id=\'n\'><feTurbulence type=\'fractalNoise\' baseFrequency=\'.8\' numOctaves=\'4\' stitchTiles=\'stitch\' /></filter><rect width=\'100%\' height=\'100%\' filter=\'url(%23n)\' opacity=\'.035\'/></svg>');}"
      }
    }
  },
  "typography": {
    "google_fonts": [
      {"name": "Space Grotesk", "weights": ["400","500","700"], "usage": "Headings/numéricos"},
      {"name": "Figtree", "weights": ["400","500","600"], "usage": "Body/UI"}
    ],
    "import_tag": "<link href=\"https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Figtree:wght@400;500;600&display=swap\" rel=\"stylesheet\">",
    "scale": {
      "h1": "text-4xl sm:text-5xl lg:text-6xl tracking-tight font-semibold font-space",
      "h2": "text-base md:text-lg font-medium font-space",
      "body": "text-sm md:text-base font-figtree leading-relaxed",
      "small": "text-xs text-muted-foreground"
    },
    "utility_classes": {
      "font-space": "[font-family:'Space_Grotesk',sans-serif]",
      "font-figtree": "[font-family:'Figtree',system-ui,sans-serif]",
      "numeral": "tabular-nums lining-nums"
    }
  },
  "buttons": {
    "tokens": {
      "--btn-radius": "0.9rem",
      "--btn-shadow": "0 10px 30px -10px hsla(173,85%,45%,.45)",
      "--btn-motion": "150ms cubic-bezier(.22,1,.36,1)"
    },
    "variants": {
      "primary": "relative inline-flex items-center justify-center rounded-[var(--btn-radius)] bg-[hsl(173,85%,45%)] text-[hsl(222,30%,8%)] px-5 py-3 font-semibold shadow-[var(--btn-shadow)] hover:bg-[hsl(173,85%,40%)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[hsl(173,85%,45%)] active:scale-[0.98] transition-colors",
      "secondary_glass": "relative inline-flex items-center justify-center rounded-[var(--btn-radius)] bg-white/5 backdrop-blur-md border border-white/10 text-foreground px-5 py-3 hover:bg-white/8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(173,85%,45%)] transition-colors",
      "ghost": "rounded-[var(--btn-radius)] px-4 py-2 hover:bg-muted/40 text-foreground"
    },
    "sizes": {"sm": "px-3 py-2 text-sm", "md": "px-5 py-3", "lg": "px-6 py-3.5 text-base"},
    "ripple_js": "export const useRipple = () => {return (e)=>{const t=e.currentTarget;const r=document.createElement('span');const d=Math.max(t.clientWidth,t.clientHeight);r.style.width=r.style.height=d+'px';r.style.left=e.clientX-t.getBoundingClientRect().left-d/2+'px';r.style.top=e.clientY-t.getBoundingClientRect().top-d/2+'px';r.className='pointer-events-none absolute rounded-full bg-white/40 animate-[ripple_600ms_ease-out]';t.appendChild(r);setTimeout(()=>r.remove(),600);}};",
    "ripple_css": "@keyframes ripple{from{transform:scale(.3);opacity:.7}to{transform:scale(2.4);opacity:0}}"
  },
  "components": {
    "use_shadcn": true,
    "paths": {
      "button": "/app/frontend/src/components/ui/button.jsx",
      "card": "/app/frontend/src/components/ui/card.jsx",
      "badge": "/app/frontend/src/components/ui/badge.jsx",
      "progress": "/app/frontend/src/components/ui/progress.jsx",
      "skeleton": "/app/frontend/src/components/ui/skeleton.jsx",
      "dialog": "/app/frontend/src/components/ui/dialog.jsx",
      "sheet": "/app/frontend/src/components/ui/sheet.jsx",
      "tabs": "/app/frontend/src/components/ui/tabs.jsx",
      "select": "/app/frontend/src/components/ui/select.jsx",
      "switch": "/app/frontend/src/components/ui/switch.jsx",
      "tooltip": "/app/frontend/src/components/ui/tooltip.jsx",
      "table": "/app/frontend/src/components/ui/table.jsx",
      "avatar": "/app/frontend/src/components/ui/avatar.jsx",
      "hover-card": "/app/frontend/src/components/ui/hover-card.jsx",
      "sonner": "/app/frontend/src/components/ui/sonner.jsx"
    },
    "custom": {
      "TimerRing.jsx": "import React from 'react';import {motion, useAnimationControls} from 'framer-motion';export const TimerRing=({seconds,total=10,warningAt=3})=>{const r=36;const c=2*Math.PI*r;const pct=Math.max(0,Math.min(1,seconds/total));const stroke=c*pct;const urgent=seconds<=warningAt;return(<div className='relative w-24 h-24' data-testid='match-timer'> <svg className='w-24 h-24 -rotate-90' viewBox='0 0 100 100' aria-hidden> <circle cx='50' cy='50' r='36' className='text-white/10' stroke='currentColor' strokeWidth='8' fill='none'/> <motion.circle cx='50' cy='50' r='36' strokeWidth='8' fill='none' strokeLinecap='round' stroke='hsl(173,85%,45%)' style={{pathLength:pct}} animate={{stroke: urgent? 'hsl(8,78%,54%)':'hsl(173,85%,45%)'}} transition={{duration:.2}} /> </svg> <div className='absolute inset-0 grid place-items-center font-space text-lg'>{seconds}s</div> </div>)};",
      "AnswerOption.jsx": "import React from 'react';import {cn} from '../lib/cn';export const AnswerOption=({label,text,state='idle',onSelect,disabled})=>{const base='relative rounded-xl border px-4 py-3 text-left cursor-pointer select-none';const tone= state==='correct'?'border-emerald-400/60 bg-emerald-400/10 ring-2 ring-emerald-400/40': state==='wrong'?'border-red-500/50 bg-red-500/5 animate-[shake_.4s_linear]':'border-white/10 bg-white/5 hover:bg-white/8';return(<button data-testid={`answer-${label}`} disabled={disabled} onClick={onSelect} className={cn(base,tone,'transition-colors')}> <span className='mr-2 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-white/10 font-space text-xs'>{label}</span>{text}</button>)};",
      "ScoreBoard.jsx": "import React from 'react';export const ScoreBoard=({me,opponent})=> (<div className='sticky top-0 z-20 grid grid-cols-2 gap-2 rounded-xl border border-white/10 bg-black/30 p-2 backdrop-blur-md' data-testid='scoreboard'> {[me,opponent].map((p,i)=>(<div key={i} className='flex items-center gap-2'> <img src={p.flag} alt='' className='h-4 w-6 rounded-sm object-cover'/> <span className='font-space font-semibold'>{p.name}</span> <span className='ml-auto rounded-md bg-white/10 px-2 py-1 font-space'>{p.score}</span></div>))}</div>);",
      "EloBadge.jsx": "import React from 'react';const map={bronce:'28 65% 46%',plata:'214 10% 76%',oro:'45 92% 54%',diamante:'173 85% 55%',maestro:'197 100% 54%',gran_maestro:'96 86% 56%'};export const EloBadge=({tier='bronce'})=> (<span className='inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-semibold' style={{background:`hsl(${map[tier]})`,color:'hsl(222 30% 8%)'}} data-testid='elo-badge'>{tier}</span>);",
      "ConfettiLayer.js": "import confetti from 'canvas-confetti';export const fireConfetti=(opts={})=>{confetti({particleCount:160,spread:70,origin:{y:.6},...opts});};",
      "ShakeKeyframes.css": "@keyframes shake{0%,100%{transform:translateX(0)}20%{transform:translateX(-3px)}40%{transform:translateX(3px)}60%{transform:translateX(-2px)}80%{transform:translateX(2px)}}"
    }
  },
  "layouts": {
    "container": "mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8",
    "grid": {
      "mobile_first": "stack en 1 columna; usa gap-6 y paddings grandes",
      "bento": "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 md:gap-6"
    },
    "screens": {
      "onboarding_login": {
        "hero": "Full-screen dark with hero_soft gradient (máx 20% viewport). Card de login centrado vertical pero layout no centrado global. Fondo con sutil noise.",
        "components": ["card", "input", "button", "sonner"],
        "cta": "Botón 'Continuar con Google/Email' con ripple. Links a registro rápido.",
        "data_testids": ["login-email-input","login-submit-button","login-google-button"]
      },
      "home_dashboard": {
        "layout": "Bento grid: CTA 'Jugar Random' (xl:span-2), Top Temas, Tema semanal, Contador de duelos, Estado Premium, Toggle DND.",
        "classes": "bento grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 md:gap-6",
        "components": ["button","card","switch","badge","progress","tabs"],
        "data_testids": ["play-random-button","weekly-topic-card","duels-remaining-chip","premium-status-card","dnd-toggle"]
      },
      "lobby_matchmaking": {
        "layout": "Lista de jugadores con avatar, bandera, ELO, ping. Barra de búsqueda Command. Botón Random prominente.",
        "components": ["command","table","select","button","avatar","tooltip"],
        "data_testids": ["matchmaking-random-button","player-row","region-select"]
      },
      "match_screen": {
        "critical": true,
        "layout": "Header fijo con ScoreBoard + TimerRing. Cuerpo: Pregunta destacada y grilla 2x3 (md) de 6 opciones. Footer con 'Pedir Pista' y estados.",
        "classes": {
          "header": "sticky top-0 z-30 flex items-center justify-between gap-3 bg-gradient-to-b from-black/40 to-transparent p-3 backdrop-blur-md",
          "question": "mt-4 rounded-2xl border border-white/10 bg-white/5 p-4 text-lg md:text-xl font-medium",
          "answers_grid": "mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3",
          "hint_bar": "mt-3 flex items-center justify-between"
        },
        "interactions": {
          "answer_states": "idle -> hover:bg-white/8; selected -> lock + progress; correct -> glow emerald; wrong -> shake + red border; disable others",
          "timer_10s": "TimerRing con cambio de color bajo 3s y pulso dramático (scale+color)",
          "hint": "Dialog de confirmación (pierde -1 punto)"
        },
        "data_testids": [
          "match-question-text","answer-A","answer-B","answer-C","answer-D","answer-E","answer-F","match-timer","request-hint-button","scoreboard"
        ]
      },
      "results_screen": {
        "layout": "Card central con resultado, cambio ELO (+/-), accuracy, tiempo promedio. Botón Revancha + Compartir.",
        "components": ["card","badge","button","sonner"],
        "effects": "Confetti al ganar; transición suave al volver al lobby.",
        "data_testids": ["result-elo-delta","result-rematch-button","result-share-button"]
      },
      "rankings": {
        "layout": "Tabs: Global, Semanal, Por tema. Table con sticky header, avatar, país, ELO, racha. Filtros a la derecha.",
        "components": ["tabs","table","select","badge","hover-card"],
        "data_testids": ["leaderboard-row","leaderboard-tab-global","leaderboard-tab-weekly","leaderboard-topic-select"]
      },
      "profile": {
        "layout": "Header con avatar grande y EloBadge. Grilla: estadísticas (recharts), historial, logros.",
        "components": ["card","badge","table","tabs"],
        "data_testids": ["profile-elo-badge","profile-elo-chart","match-history-row"]
      },
      "paywall_premium": {
        "layout": "Sección hero con glass card (blur, border), lista de beneficios, pricing tiers. CTA grande.",
        "components": ["card","badge","button","tabs"],
        "data_testids": ["premium-subscribe-button","premium-tier-card"]
      }
    }
  },
  "motion_and_microinteractions": {
    "library": "framer-motion",
    "install": "npm i framer-motion canvas-confetti",
    "principles": [
      "Duraciones 120–250ms para UI, 350–600ms para transiciones de página",
      "Easing: cubic-bezier(.22,1,.36,1)",
      "Usa transform/opacity únicamente; no transition: all"
    ],
    "patterns": {
      "page_transition": "<motion.main initial={{opacity:0,y:10}} animate={{opacity:1,y:0}} exit={{opacity:0,y:-10}} transition={{duration:.22}}/>",
      "answer_feedback": "correcto->breve glow y bloqueo; incorrecto->shake keyframes + sonner toast",
      "timer_pulse_last3s": "<motion.div animate={seconds<=3?{scale:[1,1.06,1],filter:['brightness(1)','brightness(1.2)','brightness(1)']}:{} } transition={{repeat:seconds<=3?Infinity:0,duration:.6}}/>",
      "skeletons": "/app/frontend/src/components/ui/skeleton.jsx para carga de preguntas",
      "toasts": "/app/frontend/src/components/ui/sonner.jsx con posiciones top-center"
    }
  },
  "data_and_leagues": {
    "elo_buckets": [
      {"tier":"bronce","min":0,"max":999},
      {"tier":"plata","min":1000,"max":1199},
      {"tier":"oro","min":1200,"max":1399},
      {"tier":"diamante","min":1400,"max":1599},
      {"tier":"maestro","min":1600,"max":1799},
      {"tier":"gran_maestro","min":1800,"max":9999}
    ],
    "badge_style": "Usar EloBadge con fondo sólido (no gradiente) y texto oscuro. Iconografía lucide-react: Trophy, Shield, Diamond, Crown."
  },
  "charts": {
    "library": "recharts",
    "install": "npm i recharts",
    "elo_sparkline_example": "<ResponsiveContainer width='100%' height={140}><AreaChart data={data}><defs><linearGradient id='c' x1='0' x2='0' y1='0' y2='1'><stop offset='0%' stopColor='hsl(173,85%,45%)' stopOpacity={.7}/><stop offset='100%' stopColor='hsl(173,85%,45%)' stopOpacity={0}/></linearGradient></defs><XAxis dataKey='t' hide/><YAxis hide/><Area type='monotone' dataKey='elo' stroke='hsl(173,85%,45%)' fill='url(#c)' strokeWidth={2}/></AreaChart></ResponsiveContainer>"
  },
  "icons": {
    "library": "lucide-react",
    "install": "npm i lucide-react",
    "usage": "import { Sword, Trophy, Shield, Timer, Crown, Flame, Sparkles } from 'lucide-react'"
  },
  "images_urls": [
    {
      "url": "https://images.unsplash.com/photo-1615096962549-f35ac603bf31?crop=entropy&cs=srgb&fm=jpg&q=85",
      "category": "hero-background",
      "description": "Fondo marino teal/cyan suave para onboarding y paywall (máx 20% viewport)."
    },
    {
      "url": "https://images.unsplash.com/photo-1557688543-4e2f83d6796b?crop=entropy&cs=srgb&fm=jpg&q=85",
      "category": "section-accent",
      "description": "Neblina cyan con estrellas para strip decorativo en rankings."
    },
    {
      "url": "https://images.unsplash.com/photo-1710839288352-ce7574a63f71?crop=entropy&cs=srgb&fm=jpg&q=85",
      "category": "profile-header",
      "description": "Textura azul océano para encabezado de perfil con glass card."
    }
  ],
  "accessibility": {
    "contrast": "AA mínimo. Texto sobre fondos oscuros >= 4.5:1. Usa tonos hsl(0 0% 98%)/hsl(210 6% 80%) para secundarios.",
    "focus": "Siempre ring-2 con ring-[--ring] y offset-2.",
    "reduced_motion": "Respeta prefers-reduced-motion: reduce duraciones y desactiva shake/confetti.",
    "aria": "Temporizador con aria-live=polite cada segundo. Mensajes de correcto/incorrecto via aria-live assertive.",
    "keyboard": "Todas las respuestas enfocables (role=button) con Enter/Espacio."
  },
  "testing_attributes": {
    "convention": "kebab-case por rol. Siempre incluir data-testid en botones, inputs, links, toasts y textos críticos.",
    "examples": [
      "data-testid=\"play-random-button\"",
      "data-testid=\"match-question-text\"",
      "data-testid=\"login-form-submit-button\"",
      "data-testid=\"leaderboard-row\"",
      "data-testid=\"premium-subscribe-button\""
    ]
  },
  "implementation_notes": {
    "css_apply": [
      "Añade variables de color en index.css (sección :root y .dark) con los tokens definidos.",
      "Agrega .noise-overlay y ShakeKeyframes.css a nivel global (importa en index.css)."
    ],
    "screen_scaffolds": {
      "home_cta_button": "<Button data-testid=\"play-random-button\" className=\"group relative overflow-hidden text-base md:text-lg !rounded-[var(--btn-radius)]\"><span class='relative z-10'>Jugar Random</span><span aria-hidden class='absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(255,255,255,.12),transparent_60%)] opacity-0 group-hover:opacity-100 transition-opacity'></span></Button>",
      "hint_dialog": "Usa /components/ui/dialog.jsx. Título: '¿Pedir pista? -1 punto'. Botón confirmar con data-testid=\"confirm-hint-button\"",
      "toast_usage": "import { Toaster, toast } from '../components/ui/sonner'; toast.success('¡Correcto! +2');"
    }
  },
  "library_integration": {
    "flags": {"lib": "flag-icons", "install": "npm i flag-icons", "usage": "<span className=\"fi fi-es\" />"},
    "state": {"lib": "zustand", "install": "npm i zustand", "note": "centraliza match state (timer, scores, selection)"}
  },
  "league_badges_style": {
    "shape": "capsule con borde interno sutil",
    "icon": "lucide-react según tier",
    "shadow": "0 6px 18px -8px rgba(0,0,0,.35)",
    "text_class": "font-space text-[11px] tracking-wide"
  },
  "screen_specific_details": {
    "match_timer_a11y": "Leer '3,2,1' con aria-live y cambio de color a rojo en últimos 3s.",
    "answer_grid_responsive": "1col (xs) -> 2col (sm,md) -> 3col (lg+) para 6 opciones",
    "scoreboard_persistence": "sticky top-0 con backdrop-blur; no cubrir contenido crítico"
  },
  "parallax_and_backgrounds": {
    "rule": "No superar 20% del viewport. Usar solo en headers/strips decorativos.",
    "css": ".parallax{perspective:1200px;}.parallax>*{transform-style:preserve-3d}.parallax .layer{transform:translateZ(-20px) scale(1.1)}"
  },
  "component_path": {
    "primary_sources": ["/app/frontend/src/components/ui/*"],
    "avoid_html_native": true,
    "note": "Todos los dropdowns, toasts, dialogs y calendarios deben venir de shadcn/ui."
  },
  "instructions_to_main_agent": [
    "Aplicar dark mode por defecto en <html class='dark'> con opción de claro.",
    "Inyectar Google Fonts link en index.html y utilidades font-space/font-figtree.",
    "Actualizar tokens en index.css con los definidos arriba (respetando HSL).",
    "Usar Button de shadcn para todas las CTAs y envolver con ripple (useRipple).",
    "Implementar TimerRing.jsx y AnswerOption.jsx en /app/frontend/src/components/custom/ (JS, no TSX).",
    "Añadir data-testid en cada elemento interactivo y texto crítico según convención.",
    "Integrar sonner para feedback y canvas-confetti en Results.",
    "Para rankings usar Table de shadcn con headers sticky y filas clicables.",
    "Respetar GRADIENT RESTRICTION RULE; fondos de lectura siempre sólidos.",
    "Cualquier calendario (si se usa) debe venir de /app/frontend/src/components/ui/calendar.jsx"
  ]
}


<General UI UX Design Guidelines>  
    - You must **not** apply universal transition. Eg: `transition: all`. This results in breaking transforms. Always add transitions for specific interactive elements like button, input excluding transforms
    - You must **not** center align the app container, ie do not add `.App { text-align: center; }` in the css file. This disrupts the human natural reading flow of text
   - NEVER: use AI assistant Emoji characters like`🤖🧠💭💡🔮🎯📚🎭🎬🎪🎉🎊🎁🎀🎂🍰🎈🎨🎰💰💵💳🏦💎🪙💸🤑📊📈📉💹🔢🏆🥇 etc for icons. Always use **FontAwesome cdn** or **lucid-react** library already installed in the package.json

 **GRADIENT RESTRICTION RULE**
NEVER use dark/saturated gradient combos (e.g., purple/pink) on any UI element.  Prohibited gradients: blue-500 to purple 600, purple 500 to pink-500, green-500 to blue-500, red to pink etc
NEVER use dark gradients for logo, testimonial, footer etc
NEVER let gradients cover more than 20% of the viewport.
NEVER apply gradients to text-heavy content or reading areas.
NEVER use gradients on small UI elements (<100px width).
NEVER stack multiple gradient layers in the same viewport.

**ENFORCEMENT RULE:**
    • Id gradient area exceeds 20% of viewport OR affects readability, **THEN** use solid colors

**How and where to use:**
   • Section backgrounds (not content backgrounds)
   • Hero section header content. Eg: dark to light to dark color
   • Decorative overlays and accent elements only
   • Hero section with 2-3 mild color
   • Gradients creation can be done for any angle say horizontal, vertical or diagonal

- For AI chat, voice application, **do not use purple color. Use color like light green, ocean blue, peach orange etc**

</Font Guidelines>

- Every interaction needs micro-animations - hover states, transitions, parallax effects, and entrance animations. Static = dead. 
   
- Use 2-3x more spacing than feels comfortable. Cramped designs look cheap.

- Subtle grain textures, noise overlays, custom cursors, selection states, and loading animations: separates good from extraordinary.
   
- Before generating UI, infer the visual style from the problem statement (palette, contrast, mood, motion) and immediately instantiate it by setting global design tokens (primary, secondary/accent, background, foreground, ring, state colors), rather than relying on any library defaults. Don't make the background dark as a default step, always understand problem first and define colors accordingly
    Eg: - if it implies playful/energetic, choose a colorful scheme
           - if it implies monochrome/minimal, choose a black–white/neutral scheme

**Component Reuse:**
	- Prioritize using pre-existing components from src/components/ui when applicable
	- Create new components that match the style and conventions of existing components when needed
	- Examine existing components to understand the project's component patterns before creating new ones

**IMPORTANT**: Do not use HTML based component like dropdown, calendar, toast etc. You **MUST** always use `/app/frontend/src/components/ui/ ` only as a primary components as these are modern and stylish component

**Best Practices:**
	- Use Shadcn/UI as the primary component library for consistency and accessibility
	- Import path: ./components/[component-name]

**Export Conventions:**
	- Components MUST use named exports (export const ComponentName = ...)
	- Pages MUST use default exports (export default function PageName() {...})

**Toasts:**
  - Use `sonner` for toasts"
  - Sonner component are located in `/app/src/components/ui/sonner.tsx`

Use 2–4 color gradients, subtle textures/noise overlays, or CSS-based noise to avoid flat visuals.
</General UI UX Design Guidelines>
