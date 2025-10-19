import React, { useState, useRef, useEffect } from 'react';
import { Camera, Settings, LogOut, Plus, Check, X, Clock, Calendar } from 'lucide-react';

// Mock auth - replace with real Google Auth
const MockAuthContext = React.createContext();

export default function CouponApp() {
  const [user, setUser] = useState(null);
  const [coupons, setCoupons] = useState([]);
  const [settings, setSettings] = useState({
    autoDeleteExpired: false,
    autoDeleteClaimed: false,
    notifyBeforeExpiry: 3,
    syncGoogleCalendar: false,
  });
  const [view, setView] = useState('coupons'); // 'coupons', 'settings', 'camera'
  const [loading, setLoading] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const cameraRef = useRef(null);
  const videoRef = useRef(null);

  useEffect(() => {
    // Simulate user login
    setUser({ id: '123', email: 'user@example.com', name: 'John Doe' });
    // Load mock coupons
    setCoupons([
      {
        id: '1',
        code: 'SAVE20',
        title: 'Save 20% on Electronics',
        provider: 'TechStore',
        discount: '20% off',
        expiryDate: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000),
        deadline: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000),
        terms: 'Valid on purchases over $50',
        claimed: false,
        scannedAt: new Date(),
      },
      {
        id: '2',
        code: 'EXPIRED10',
        title: 'Free Shipping',
        provider: 'ShopMart',
        discount: 'Free shipping',
        expiryDate: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
        deadline: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
        terms: 'On orders over $25',
        claimed: false,
        scannedAt: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000),
      },
    ]);
  }, []);

  const handleCameraStart = async () => {
    setView('camera');
    setTimeout(() => {
      if (videoRef.current) {
        navigator.mediaDevices
          .getUserMedia({ video: { facingMode: 'environment' } })
          .then((stream) => {
            videoRef.current.srcObject = stream;
          })
          .catch((err) => console.error('Camera error:', err));
      }
    }, 100);
  };

  const handleCapture = async () => {
    if (videoRef.current) {
      setLoading(true);
      const canvas = document.createElement('canvas');
      canvas.width = videoRef.current.videoWidth;
      canvas.height = videoRef.current.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(videoRef.current, 0, 0);

      // Mock OCR processing
      const imageData = canvas.toDataURL();
      const mockCoupon = {
        id: Date.now().toString(),
        code: `CODE${Math.random().toString(36).substr(2, 5).toUpperCase()}`,
        title: 'Special Discount Offer',
        provider: 'MerchantName',
        discount: '15% off or $10 discount',
        expiryDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000),
        deadline: new Date(Date.now() + 25 * 24 * 60 * 60 * 1000),
        terms: 'Terms visible in image',
        claimed: false,
        scannedAt: new Date(),
      };

      setCoupons([mockCoupon, ...coupons]);
      setLoading(false);
      setView('coupons');
    }
  };

  const handleToggleClaimed = (id) => {
    setCoupons(
      coupons.map((c) => (c.id === id ? { ...c, claimed: !c.claimed } : c))
    );
  };

  const handleDeleteCoupon = (id) => {
    setCoupons(coupons.filter((c) => c.id !== id));
  };

  const handleLogout = () => {
    setUser(null);
    setCoupons([]);
  };

  const isExpired = (coupon) => new Date() > coupon.expiryDate;
  const daysUntilExpiry = (coupon) => {
    const days = Math.ceil(
      (coupon.expiryDate - new Date()) / (1000 * 60 * 60 * 24)
    );
    return days;
  };

  const activeCoupons = coupons.filter(
    (c) => !isExpired(c) && !c.claimed
  ).length;
  const expiredCoupons = coupons.filter((c) => isExpired(c)).length;

  if (!user) {
    return (
      <div className="h-screen w-full bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center">
        <div className="text-center text-white">
          <Camera size={64} className="mx-auto mb-4" />
          <h1 className="text-4xl font-bold mb-2">CouponSnap</h1>
          <p className="text-xl mb-8">Scan & Manage Your Coupons</p>
          <button
            onClick={() =>
              setUser({
                id: '123',
                email: 'user@example.com',
                name: 'John Doe',
              })
            }
            className="bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-blue-50"
          >
            Sign in with Google
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gray-50 flex flex-col pb-20">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">CouponSnap</h1>
            <p className="text-sm text-gray-500">{user.email}</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="p-2 hover:bg-gray-100 rounded-lg"
            >
              <Settings size={24} className="text-gray-600" />
            </button>
            <button
              onClick={handleLogout}
              className="p-2 hover:bg-gray-100 rounded-lg"
            >
              <LogOut size={24} className="text-gray-600" />
            </button>
          </div>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="bg-white border-b">
          <div className="max-w-4xl mx-auto px-4 py-4 space-y-4">
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={settings.autoDeleteExpired}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    autoDeleteExpired: e.target.checked,
                  })
                }
                className="w-4 h-4"
              />
              <span>Auto-delete expired coupons</span>
            </label>
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={settings.autoDeleteClaimed}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    autoDeleteClaimed: e.target.checked,
                  })
                }
                className="w-4 h-4"
              />
              <span>Auto-delete claimed coupons</span>
            </label>
            <label className="flex items-center gap-3">
              <input
                type="checkbox"
                checked={settings.syncGoogleCalendar}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    syncGoogleCalendar: e.target.checked,
                  })
                }
                className="w-4 h-4"
              />
              <span>Sync with Google Calendar</span>
            </label>
            <div>
              <label className="block text-sm mb-2">
                Notify before expiry (days)
              </label>
              <input
                type="number"
                value={settings.notifyBeforeExpiry}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    notifyBeforeExpiry: parseInt(e.target.value),
                  })
                }
                min="1"
                className="border rounded px-3 py-2 w-full"
              />
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 max-w-4xl w-full mx-auto px-4 py-6">
        {view === 'camera' ? (
          <div className="space-y-4">
            <video
              ref={videoRef}
              autoPlay
              className="w-full rounded-lg bg-black"
            />
            <div className="flex gap-4">
              <button
                onClick={() => setView('coupons')}
                className="flex-1 bg-gray-500 text-white py-3 rounded-lg font-semibold hover:bg-gray-600"
              >
                Cancel
              </button>
              <button
                onClick={handleCapture}
                disabled={loading}
                className="flex-1 bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400"
              >
                {loading ? 'Processing...' : 'Capture'}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Stats */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-white p-4 rounded-lg border">
                <p className="text-2xl font-bold text-blue-600">
                  {coupons.length}
                </p>
                <p className="text-sm text-gray-600">Total Coupons</p>
              </div>
              <div className="bg-white p-4 rounded-lg border">
                <p className="text-2xl font-bold text-green-600">
                  {activeCoupons}
                </p>
                <p className="text-sm text-gray-600">Active</p>
              </div>
              <div className="bg-white p-4 rounded-lg border">
                <p className="text-2xl font-bold text-red-600">
                  {expiredCoupons}
                </p>
                <p className="text-sm text-gray-600">Expired</p>
              </div>
            </div>

            {/* Coupons List */}
            <div className="space-y-3">
              {coupons.length === 0 ? (
                <div className="text-center py-12 bg-white rounded-lg border-2 border-dashed">
                  <Camera size={48} className="mx-auto text-gray-300 mb-2" />
                  <p className="text-gray-500">No coupons yet. Start scanning!</p>
                </div>
              ) : (
                coupons.map((coupon) => {
                  const expired = isExpired(coupon);
                  return (
                    <div
                      key={coupon.id}
                      className={`bg-white p-4 rounded-lg border ${
                        expired ? 'opacity-60' : ''
                      } ${coupon.claimed ? 'bg-gray-50' : ''}`}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <div className="flex-1">
                          <h3 className="font-bold text-gray-900">
                            {coupon.title}
                          </h3>
                          <p className="text-sm text-gray-600">
                            {coupon.provider}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="font-mono font-bold text-blue-600">
                            {coupon.code}
                          </p>
                          <p className="text-sm font-semibold text-green-600">
                            {coupon.discount}
                          </p>
                        </div>
                      </div>

                      <p className="text-xs text-gray-600 mb-3">
                        {coupon.terms}
                      </p>

                      <div className="flex gap-2 text-xs mb-3">
                        {expired && (
                          <span className="bg-red-100 text-red-800 px-2 py-1 rounded">
                            Expired
                          </span>
                        )}
                        {!expired && (
                          <span className="bg-green-100 text-green-800 px-2 py-1 rounded flex items-center gap-1">
                            <Clock size={12} />
                            {daysUntilExpiry(coupon)} days left
                          </span>
                        )}
                        {coupon.claimed && (
                          <span className="bg-gray-200 text-gray-800 px-2 py-1 rounded">
                            Claimed
                          </span>
                        )}
                      </div>

                      <div className="flex gap-2">
                        <button
                          onClick={() => handleToggleClaimed(coupon.id)}
                          className={`flex-1 py-2 px-3 rounded text-sm font-semibold flex items-center justify-center gap-2 ${
                            coupon.claimed
                              ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                              : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
                          }`}
                        >
                          <Check size={16} />
                          {coupon.claimed ? 'Mark Active' : 'Mark Claimed'}
                        </button>
                        <button
                          onClick={() => handleDeleteCoupon(coupon.id)}
                          className="py-2 px-3 rounded text-sm font-semibold bg-red-100 text-red-700 hover:bg-red-200"
                        >
                          <X size={16} />
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}
      </div>

      {/* Floating Action Button */}
      {view === 'coupons' && (
        <button
          onClick={handleCameraStart}
          className="fixed bottom-8 right-8 bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700 active:scale-95 transition"
        >
          <Plus size={32} />
        </button>
      )}
    </div>
  );
}