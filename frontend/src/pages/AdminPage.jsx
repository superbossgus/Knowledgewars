import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import api from '../lib/api';
import { toast } from 'sonner';
import { 
  ArrowLeft, Shield, Plus, Trash2, ToggleLeft, ToggleRight, 
  Users, Gamepad2, DollarSign, Ticket, Gift, Percent 
} from 'lucide-react';

export default function AdminPage() {
  const navigate = useNavigate();
  const [authenticated, setAuthenticated] = useState(false);
  const [adminSecret, setAdminSecret] = useState('');
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [coupons, setCoupons] = useState([]);
  const [showCreateCoupon, setShowCreateCoupon] = useState(false);
  const [newCoupon, setNewCoupon] = useState({
    code: '',
    coupon_type: 'free_games',
    value: 10,
    max_uses: 100,
    expiration_days: 30,
    description: ''
  });

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await api.get('/api/admin/stats', {
        headers: { Authorization: `Bearer ${adminSecret}` }
      });
      setStats(response.data);
      setAuthenticated(true);
      localStorage.setItem('admin_secret', adminSecret);
      loadCoupons();
    } catch (error) {
      toast.error('Credenciales de administrador inválidas');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const savedSecret = localStorage.getItem('admin_secret');
    if (savedSecret) {
      setAdminSecret(savedSecret);
      verifyAdmin(savedSecret);
    }
  }, []);

  const verifyAdmin = async (secret) => {
    try {
      const response = await api.get('/api/admin/stats', {
        headers: { Authorization: `Bearer ${secret}` }
      });
      setStats(response.data);
      setAuthenticated(true);
      loadCoupons();
    } catch (error) {
      localStorage.removeItem('admin_secret');
    }
  };

  const loadCoupons = async () => {
    try {
      const response = await api.get('/api/admin/coupons', {
        headers: { Authorization: `Bearer ${adminSecret || localStorage.getItem('admin_secret')}` }
      });
      setCoupons(response.data.coupons || []);
    } catch (error) {
      toast.error('Error al cargar cupones');
    }
  };

  const handleCreateCoupon = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post('/api/admin/coupons/create', newCoupon, {
        headers: { Authorization: `Bearer ${adminSecret || localStorage.getItem('admin_secret')}` }
      });
      toast.success('Cupón creado exitosamente');
      setShowCreateCoupon(false);
      setNewCoupon({
        code: '',
        coupon_type: 'free_games',
        value: 10,
        max_uses: 100,
        expiration_days: 30,
        description: ''
      });
      loadCoupons();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al crear cupón');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleCoupon = async (code) => {
    try {
      const response = await api.patch(`/api/admin/coupons/${code}/toggle`, {}, {
        headers: { Authorization: `Bearer ${adminSecret || localStorage.getItem('admin_secret')}` }
      });
      toast.success(`Cupón ${response.data.active ? 'activado' : 'desactivado'}`);
      loadCoupons();
    } catch (error) {
      toast.error('Error al cambiar estado del cupón');
    }
  };

  const handleDeleteCoupon = async (code) => {
    if (!confirm(`¿Eliminar cupón ${code}?`)) return;
    try {
      await api.delete(`/api/admin/coupons/${code}`, {
        headers: { Authorization: `Bearer ${adminSecret || localStorage.getItem('admin_secret')}` }
      });
      toast.success('Cupón eliminado');
      loadCoupons();
    } catch (error) {
      toast.error('Error al eliminar cupón');
    }
  };

  const handleResetAllElos = async () => {
    if (!confirm('⚠️ ¿SEGURO que quieres resetear TODOS los usuarios a BRONCE III (500 ELO)? Esta acción no se puede deshacer.')) return;
    if (!confirm('⚠️ CONFIRMAR: Esto afectará a TODOS los jugadores. ¿Continuar?')) return;
    
    setLoading(true);
    try {
      const response = await api.post('/api/admin/reset-all-elos', {}, {
        headers: { Authorization: `Bearer ${adminSecret || localStorage.getItem('admin_secret')}` }
      });
      toast.success(response.data.message);
      // Reload stats
      const statsResponse = await api.get('/api/admin/stats', {
        headers: { Authorization: `Bearer ${adminSecret || localStorage.getItem('admin_secret')}` }
      });
      setStats(statsResponse.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al resetear ELOs');
    } finally {
      setLoading(false);
    }
  };

  const handleGiveGamesToAll = async () => {
    const games = prompt('¿Cuántas partidas gratis quieres dar a TODOS los usuarios? (1-100)');
    if (!games) return;
    
    const gamesNum = parseInt(games);
    if (isNaN(gamesNum) || gamesNum < 1 || gamesNum > 100) {
      toast.error('Ingresa un número válido entre 1 y 100');
      return;
    }
    
    if (!confirm(`¿Dar ${gamesNum} partidas gratis a TODOS los usuarios?`)) return;
    
    setLoading(true);
    try {
      const response = await api.post(`/api/admin/give-games?games=${gamesNum}`, {}, {
        headers: { Authorization: `Bearer ${adminSecret || localStorage.getItem('admin_secret')}` }
      });
      toast.success(response.data.message);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al dar partidas');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('admin_secret');
    setAuthenticated(false);
    setAdminSecret('');
  };

  // Login Screen
  if (!authenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 hero-gradient">
        <div className="noise-overlay" />
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md relative z-10"
        >
          <div className="text-center mb-8">
            <Shield className="w-16 h-16 mx-auto mb-4 text-[hsl(25,100%,50%)]" style={{ filter: 'drop-shadow(0 0 15px hsl(25 100% 50%))' }} />
            <h1 className="text-3xl font-extrabold font-brand text-white">Panel Admin</h1>
            <p className="text-muted-foreground">Gestión de Knowledge Wars</p>
          </div>

          <div className="bg-[hsl(220,28%,10%,0.85)] backdrop-blur-xl border-2 border-[hsl(25,100%,50%,0.3)] rounded-2xl p-6">
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-sm font-bold mb-2 text-white">Clave de Administrador</label>
                <input
                  type="password"
                  value={adminSecret}
                  onChange={(e) => setAdminSecret(e.target.value)}
                  placeholder="Ingresa la clave secreta"
                  className="w-full px-4 py-3 bg-background/50 border-2 border-[hsl(25,100%,50%,0.3)] rounded-xl text-white placeholder-muted-foreground focus:ring-2 focus:ring-[hsl(25,100%,50%)] focus:outline-none"
                  data-testid="admin-secret-input"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full btn-primary py-3 disabled:opacity-50"
              >
                {loading ? 'Verificando...' : 'Acceder'}
              </button>
            </form>
            
            <button
              onClick={() => navigate('/login')}
              className="flex items-center gap-2 mt-4 text-muted-foreground hover:text-white transition-colors w-full justify-center"
            >
              <ArrowLeft className="w-4 h-4" />
              Volver al inicio
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  // Admin Dashboard
  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8 relative z-10">
      <div className="container mx-auto max-w-6xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-[hsl(25,100%,50%)]" />
            <h1 className="text-2xl font-extrabold font-brand text-white">Panel Admin</h1>
          </div>
          <button
            onClick={handleLogout}
            className="btn-secondary-glass px-4 py-2 text-sm"
          >
            Cerrar Sesión
          </button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-card/60 backdrop-blur-xl border-2 border-[hsl(220,100%,50%,0.3)] rounded-xl p-4">
            <Users className="w-8 h-8 text-[hsl(220,100%,50%)] mb-2" />
            <div className="text-3xl font-extrabold text-white">{stats?.total_users || 0}</div>
            <div className="text-sm text-muted-foreground">Usuarios</div>
          </div>
          <div className="bg-card/60 backdrop-blur-xl border-2 border-[hsl(25,100%,50%,0.3)] rounded-xl p-4">
            <Gamepad2 className="w-8 h-8 text-[hsl(25,100%,50%)] mb-2" />
            <div className="text-3xl font-extrabold text-white">{stats?.total_matches || 0}</div>
            <div className="text-sm text-muted-foreground">Partidas</div>
          </div>
          <div className="bg-card/60 backdrop-blur-xl border-2 border-[hsl(45,92%,48%,0.3)] rounded-xl p-4">
            <DollarSign className="w-8 h-8 text-[hsl(45,92%,48%)] mb-2" />
            <div className="text-3xl font-extrabold text-white">${stats?.total_revenue_mxn || 0}</div>
            <div className="text-sm text-muted-foreground">Ingresos (MXN)</div>
          </div>
          <div className="bg-card/60 backdrop-blur-xl border-2 border-[hsl(140,100%,50%,0.3)] rounded-xl p-4">
            <Ticket className="w-8 h-8 text-[hsl(140,100%,50%)] mb-2" />
            <div className="text-3xl font-extrabold text-white">{stats?.active_coupons || 0}</div>
            <div className="text-sm text-muted-foreground">Cupones Activos</div>
          </div>
        </div>

        {/* Admin Actions */}
        <div className="bg-card/60 backdrop-blur-xl border-2 border-[hsl(340,80%,50%,0.3)] rounded-2xl p-6 mb-8">
          <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-4">
            <Shield className="w-6 h-6 text-[hsl(340,80%,50%)]" />
            Acciones de Administrador
          </h2>
          <p className="text-sm text-muted-foreground mb-4">
            ⚠️ Estas acciones afectan a TODOS los usuarios. Usar con precaución.
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Reset All ELOs */}
            <div className="p-4 bg-muted/20 rounded-xl border border-[hsl(340,80%,50%,0.3)]">
              <h3 className="font-bold text-white mb-2">🔄 Resetear Todos los ELOs</h3>
              <p className="text-sm text-muted-foreground mb-3">
                Todos los usuarios volverán a BRONCE III (500 ELO). Útil para nueva temporada.
              </p>
              <button
                onClick={handleResetAllElos}
                disabled={loading}
                className="w-full py-2 px-4 bg-[hsl(340,80%,50%)] hover:bg-[hsl(340,80%,45%)] text-white font-bold rounded-xl transition-all disabled:opacity-50"
              >
                {loading ? 'Procesando...' : 'Resetear Todos a BRONCE III'}
              </button>
            </div>
            
            {/* Give Games to All */}
            <div className="p-4 bg-muted/20 rounded-xl border border-[hsl(140,100%,40%,0.3)]">
              <h3 className="font-bold text-white mb-2">🎁 Dar Partidas Gratis</h3>
              <p className="text-sm text-muted-foreground mb-3">
                Regala partidas a todos los usuarios. Ideal para promociones o eventos.
              </p>
              <button
                onClick={handleGiveGamesToAll}
                disabled={loading}
                className="w-full py-2 px-4 bg-[hsl(140,100%,35%)] hover:bg-[hsl(140,100%,30%)] text-white font-bold rounded-xl transition-all disabled:opacity-50"
              >
                {loading ? 'Procesando...' : 'Dar Partidas a Todos'}
              </button>
            </div>
          </div>
        </div>

        {/* Coupons Management */}
        <div className="bg-card/60 backdrop-blur-xl border-2 border-[hsl(220,100%,50%,0.3)] rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Gift className="w-6 h-6 text-[hsl(220,100%,50%)]" />
              Gestión de Cupones
            </h2>
            <button
              onClick={() => setShowCreateCoupon(!showCreateCoupon)}
              className="btn-primary px-4 py-2 text-sm flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Crear Cupón
            </button>
          </div>

          {/* Create Coupon Form */}
          {showCreateCoupon && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="mb-6 p-4 bg-muted/20 rounded-xl border border-[hsl(220,100%,50%,0.2)]"
            >
              <form onSubmit={handleCreateCoupon} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-bold mb-1 text-white">Código</label>
                  <input
                    type="text"
                    required
                    value={newCoupon.code}
                    onChange={(e) => setNewCoupon({...newCoupon, code: e.target.value.toUpperCase()})}
                    placeholder="CUPON10"
                    className="w-full px-3 py-2 bg-background/50 border border-white/20 rounded-lg text-white uppercase"
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold mb-1 text-white">Tipo</label>
                  <select
                    value={newCoupon.coupon_type}
                    onChange={(e) => setNewCoupon({...newCoupon, coupon_type: e.target.value})}
                    className="w-full px-3 py-2 bg-background/80 border border-white/20 rounded-lg text-white"
                  >
                    <option value="free_games">Partidas Gratis</option>
                    <option value="discount">Descuento %</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-bold mb-1 text-white">
                    {newCoupon.coupon_type === 'free_games' ? 'Partidas Gratis' : 'Descuento %'}
                  </label>
                  <input
                    type="number"
                    required
                    min="1"
                    max={newCoupon.coupon_type === 'discount' ? 100 : 1000}
                    value={newCoupon.value}
                    onChange={(e) => setNewCoupon({...newCoupon, value: parseInt(e.target.value)})}
                    className="w-full px-3 py-2 bg-background/50 border border-white/20 rounded-lg text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold mb-1 text-white">Usos Máximos</label>
                  <input
                    type="number"
                    required
                    min="1"
                    value={newCoupon.max_uses}
                    onChange={(e) => setNewCoupon({...newCoupon, max_uses: parseInt(e.target.value)})}
                    className="w-full px-3 py-2 bg-background/50 border border-white/20 rounded-lg text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold mb-1 text-white">Días de Validez</label>
                  <input
                    type="number"
                    required
                    min="1"
                    value={newCoupon.expiration_days}
                    onChange={(e) => setNewCoupon({...newCoupon, expiration_days: parseInt(e.target.value)})}
                    className="w-full px-3 py-2 bg-background/50 border border-white/20 rounded-lg text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold mb-1 text-white">Descripción</label>
                  <input
                    type="text"
                    value={newCoupon.description}
                    onChange={(e) => setNewCoupon({...newCoupon, description: e.target.value})}
                    placeholder="Promoción especial"
                    className="w-full px-3 py-2 bg-background/50 border border-white/20 rounded-lg text-white"
                  />
                </div>
                <div className="md:col-span-2 flex justify-end gap-2">
                  <button type="button" onClick={() => setShowCreateCoupon(false)} className="btn-secondary-glass px-4 py-2">
                    Cancelar
                  </button>
                  <button type="submit" disabled={loading} className="btn-primary px-6 py-2">
                    {loading ? 'Creando...' : 'Crear Cupón'}
                  </button>
                </div>
              </form>
            </motion.div>
          )}

          {/* Coupons Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="px-4 py-3 text-left text-sm font-bold text-white">Código</th>
                  <th className="px-4 py-3 text-left text-sm font-bold text-white">Tipo</th>
                  <th className="px-4 py-3 text-center text-sm font-bold text-white">Valor</th>
                  <th className="px-4 py-3 text-center text-sm font-bold text-white">Usos</th>
                  <th className="px-4 py-3 text-center text-sm font-bold text-white">Estado</th>
                  <th className="px-4 py-3 text-right text-sm font-bold text-white">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {coupons.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                      No hay cupones creados
                    </td>
                  </tr>
                ) : (
                  coupons.map((coupon) => (
                    <tr key={coupon.code} className="border-b border-white/5 hover:bg-white/5">
                      <td className="px-4 py-3">
                        <span className="font-mono font-bold text-[hsl(220,100%,70%)]">{coupon.code}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-bold ${
                          coupon.coupon_type === 'free_games' 
                            ? 'bg-[hsl(45,92%,48%,0.2)] text-[hsl(45,92%,48%)]'
                            : 'bg-[hsl(220,100%,50%,0.2)] text-[hsl(220,100%,70%)]'
                        }`}>
                          {coupon.coupon_type === 'free_games' ? (
                            <><Gift className="w-3 h-3" /> Partidas</>
                          ) : (
                            <><Percent className="w-3 h-3" /> Descuento</>
                          )}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center font-bold text-white">
                        {coupon.coupon_type === 'free_games' ? `${coupon.value} partidas` : `${coupon.value}%`}
                      </td>
                      <td className="px-4 py-3 text-center text-muted-foreground">
                        {coupon.uses || 0} / {coupon.max_uses}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`inline-block px-2 py-1 rounded-lg text-xs font-bold ${
                          coupon.active ? 'bg-[hsl(140,100%,50%,0.2)] text-[hsl(140,100%,50%)]' : 'bg-[hsl(0,100%,50%,0.2)] text-[hsl(0,100%,60%)]'
                        }`}>
                          {coupon.active ? 'Activo' : 'Inactivo'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleToggleCoupon(coupon.code)}
                            className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                            title={coupon.active ? 'Desactivar' : 'Activar'}
                          >
                            {coupon.active ? (
                              <ToggleRight className="w-5 h-5 text-[hsl(140,100%,50%)]" />
                            ) : (
                              <ToggleLeft className="w-5 h-5 text-muted-foreground" />
                            )}
                          </button>
                          <button
                            onClick={() => handleDeleteCoupon(coupon.code)}
                            className="p-2 rounded-lg hover:bg-[hsl(0,100%,50%,0.2)] transition-colors"
                            title="Eliminar"
                          >
                            <Trash2 className="w-5 h-5 text-[hsl(0,100%,60%)]" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
