import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence, animate } from 'framer-motion'
import { LineChart, Line, XAxis, Tooltip, ResponsiveContainer } from 'recharts'
import './App.css'
import { auth, googleProvider } from './firebase'
import { 
  signInWithPopup, 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword,
  RecaptchaVerifier,
  signInWithPhoneNumber
} from 'firebase/auth'

const chartData = [
  { time: '10am', rev: 400 },
  { time: '12pm', rev: 800 },
  { time: '2pm', rev: 1200 },
  { time: '4pm', rev: 1600 },
  { time: '6pm', rev: 2400 },
  { time: '8pm', rev: 3899 }
];

const AnimatedNumber = ({ value, prefix = "" }: { value: number, prefix?: string }) => {
  const nodeRef = useRef<HTMLSpanElement>(null);
  
  useEffect(() => {
    const node = nodeRef.current;
    if (!node) return;
    
    const controls = animate(0, value, {
      duration: 1.2,
      ease: "easeOut",
      onUpdate: (v) => {
        node.textContent = prefix + Math.floor(v).toLocaleString();
      },
    });
    
    return controls.stop;
  }, [value, prefix]);
  
  return <span ref={nodeRef}>{prefix}0</span>;
};

const ProductCard = ({ p, pIdx, handleActionMessage }: { p: any, pIdx: number, handleActionMessage: (msg: string) => void }) => {
  const [imgSrc, setImgSrc] = useState<string | null>(null);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => {
      // Primary: AI Generated Product Photography
      setImgSrc(`https://image.pollinations.ai/prompt/product%20photography%20of%20a%20${encodeURIComponent(p.title)}?width=400&height=400&nologo=true&seed=${p.sku || Math.floor(Math.random()*1000)}`);
    }, pIdx * 1200); // 1.2s stagger to safely bypass rate limits
    return () => clearTimeout(timer);
  }, [p.title, p.sku, pIdx]);

  // Fallback: Real stock photo from Flickr if AI rate-limits
  const getFallbackUrl = () => {
    const keywords = p.title.split(' ').filter(w => w.length > 2).join(',');
    return `https://loremflickr.com/400/400/${encodeURIComponent(keywords)}?lock=${pIdx + 1}`;
  };

  return (
    <div className="product-card">
      {imgSrc ? (
        <img 
          src={imgSrc} 
          alt={p.title} 
          className="product-image" 
          onError={(e) => {
            if (!hasError) {
              setHasError(true);
              e.currentTarget.src = getFallbackUrl();
            } else {
              e.currentTarget.src = `https://placehold.co/400x400/f3f4f6/9ca3af.png?text=${encodeURIComponent(p.title)}`;
            }
          }}
        />
      ) : (
        <div className="product-image" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
           <span style={{color: '#9CA3AF', fontSize: '12px'}}>Generating...</span>
        </div>
      )}
      <h3>{p.title}</h3>
      <p>₹{Math.floor(p.price_paise / 100)}</p>
      <button onClick={() => handleActionMessage(`add ${p.sku} ${p.price_paise}`)}>Add</button>
    </div>
  );
};

interface AuditEvent {
  time: string;
  text: string;
  type: 'info' | 'success' | 'warning' | 'error';
}

const InventoryTab = () => {
  const [products, setProducts] = useState<any[]>([]);
  
  useEffect(() => {
    fetch('http://localhost:8000/v1/admin/catalog')
      .then(res => res.json())
      .then(data => setProducts(data.data || []))
      .catch(err => console.error(err));
  }, []);

  return (
    <motion.div className="card" style={{ padding: '24px', margin: '20px', minHeight: '600px' }} initial={{opacity:0}} animate={{opacity:1}}>
      <h2 style={{ fontSize: '20px', marginBottom: '20px' }}>AI Generated Inventory ({products.length})</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '20px' }}>
        {products.map((p, i) => (
          <div key={i} style={{ border: '1px solid #E5E7EB', borderRadius: '8px', padding: '16px' }}>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '15px' }}>{p.title}</h4>
            <p style={{ margin: '0 0 8px 0', color: '#6B7280', fontSize: '13px' }}>SKU: {p.sku}</p>
            <p style={{ margin: 0, fontWeight: 600 }}>₹{Math.floor(p.price_paise / 100)}</p>
          </div>
        ))}
      </div>
    </motion.div>
  );
};

const SettingsTab = () => {
  const [config, setConfig] = useState({ max_order_paise: 0, max_discount_pct: 0 });
  const [saved, setSaved] = useState(false);
  
  useEffect(() => {
    fetch('http://localhost:8000/v1/admin/config')
      .then(res => res.json())
      .then(data => setConfig(data))
      .catch(err => console.error(err));
  }, []);

  const handleSave = () => {
    fetch('http://localhost:8000/v1/admin/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        max_order_paise: Number(config.max_order_paise),
        max_discount_pct: Number(config.max_discount_pct)
      })
    }).then(() => {
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    });
  };

  return (
    <motion.div className="card" style={{ padding: '24px', margin: '20px', maxWidth: '600px' }} initial={{opacity:0}} animate={{opacity:1}}>
      <h2 style={{ fontSize: '20px', marginBottom: '24px' }}>Guardrail Configuration</h2>
      
      <div style={{ marginBottom: '20px' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>Max Order Limit (₹)</label>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <input 
            type="range" 
            min="1000" 
            max="100000" 
            step="1000"
            value={Math.floor(config.max_order_paise / 100)} 
            onChange={(e) => setConfig({...config, max_order_paise: Number(e.target.value) * 100})}
            style={{ flex: 1 }}
          />
          <span style={{ fontWeight: 600, width: '80px', textAlign: 'right' }}>₹{Math.floor(config.max_order_paise / 100)}</span>
        </div>
      </div>

      <div style={{ marginBottom: '32px' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>Max Agent Discount (%)</label>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <input 
            type="range" 
            min="0" 
            max="50" 
            step="1"
            value={config.max_discount_pct} 
            onChange={(e) => setConfig({...config, max_discount_pct: Number(e.target.value)})}
            style={{ flex: 1 }}
          />
          <span style={{ fontWeight: 600, width: '80px', textAlign: 'right' }}>{config.max_discount_pct}%</span>
        </div>
      </div>

      <button 
        onClick={handleSave}
        style={{ background: saved ? '#10B981' : '#111', color: 'white', padding: '10px 20px', borderRadius: '6px', border: 'none', cursor: 'pointer', transition: 'all 0.2s' }}
      >
        {saved ? 'Settings Saved' : 'Apply Guardrails Now'}
      </button>
    </motion.div>
  );
};

interface MessageData {
  role: 'user' | 'assistant' | 'system';
  content: string;
  action?: string;
  data?: any;
}

function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'inventory' | 'settings'>('dashboard')
  const [isListening, setIsListening] = useState(false)
  const recognitionRef = useRef<any>(null)
  
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isSignUp, setIsSignUp] = useState(false)
  const [messages, setMessages] = useState<MessageData[]>([])
  const [input, setInput] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [auditLogs, setAuditLogs] = useState<AuditEvent[]>([])
  
  // Auth Form State
  const [authMode, setAuthMode] = useState<'phone' | 'email'>('email')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [otp, setOtp] = useState('')
  const [otpSent, setOtpSent] = useState(false)
  const [confirmationResult, setConfirmationResult] = useState<any>(null)
  const [authError, setAuthError] = useState('')
  
  // Ledger State
  const [sessionsCount, setSessionsCount] = useState(() => parseInt(localStorage.getItem('sessionsCount') || '12'))
  const [ordersCount, setOrdersCount] = useState(() => parseInt(localStorage.getItem('ordersCount') || '7'))
  const [revenue, setRevenue] = useState(() => parseInt(localStorage.getItem('revenue') || '8940'))

  useEffect(() => { localStorage.setItem('sessionsCount', sessionsCount.toString()); }, [sessionsCount]);
  useEffect(() => { localStorage.setItem('ordersCount', ordersCount.toString()); }, [ordersCount]);
  useEffect(() => { localStorage.setItem('revenue', revenue.toString()); }, [revenue]);

  const addAuditLog = (text: string, type: 'neutral' | 'action' | 'success' = 'neutral') => {
    const time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
    setAuditLogs(prev => [...prev, { time, text, type }]);
  }

  // --- Auth Handlers ---
  const handleGoogleSignIn = async () => {
    try {
      setAuthError('')
      await signInWithPopup(auth, googleProvider)
      setIsAuthenticated(true)
    } catch (e: any) {
      setAuthError(e.message)
    }
  }

  const handleEmailAuth = async () => {
    try {
      setAuthError('')
      if (isSignUp) {
        await createUserWithEmailAndPassword(auth, email, password)
      } else {
        await signInWithEmailAndPassword(auth, email, password)
      }
      setIsAuthenticated(true)
    } catch (e: any) {
      setAuthError(e.message)
    }
  }

  const setUpRecaptcha = () => {
    if (!(window as any).recaptchaVerifier) {
      (window as any).recaptchaVerifier = new RecaptchaVerifier(auth, 'recaptcha-container', {
        size: 'invisible'
      });
    }
  }

  const handlePhoneAuth = async () => {
    try {
      setAuthError('')
      setUpRecaptcha();
      const appVerifier = (window as any).recaptchaVerifier;
      const confirmResult = await signInWithPhoneNumber(auth, phoneNumber, appVerifier);
      setConfirmationResult(confirmResult);
      setOtpSent(true);
    } catch (e: any) {
      setAuthError(e.message)
    }
  }

  const handleVerifyOtp = async () => {
    try {
      setAuthError('')
      await confirmationResult.confirm(otp);
      setIsAuthenticated(true);
    } catch (e: any) {
      setAuthError("Invalid OTP")
    }
  }

  // Session Init
  useEffect(() => {
    if (!isAuthenticated) return;
    
    async function initSession() {
      try {
        const res = await fetch('http://localhost:8000/v1/sessions', { method: 'POST' })
        const data = await res.json()
        setSessionId(data.session_id)
        
        const shortId = data.session_id.substring(0,8);
        addAuditLog(`Session started: ${shortId}`, 'neutral');
        setSessionsCount(prev => prev + 1);
        
        setMessages([{role: 'assistant', content: 'Hi! I can help you find something from Meera\'s Store. What are you looking for?'}])
      } catch (e) {
        console.error("Failed to init session", e)
      }
    }
    initSession()
  }, [isAuthenticated])

  const [transcript, setTranscript] = useState('')
  const latestSessionId = useRef(sessionId);
  const latestExecuteChat = useRef(executeChat);

  useEffect(() => {
    latestSessionId.current = sessionId;
  }, [sessionId]);

  useEffect(() => {
    latestExecuteChat.current = executeChat;
  }, [executeChat]);

  // Voice AI Logic
  useEffect(() => {
    if (typeof window !== 'undefined' && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = true; // Show results as they speak for real-time speed
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event: any) => {
        let currentTranscript = '';
        let isFinal = false;

        for (let i = 0; i < event.results.length; i++) {
          currentTranscript += event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            isFinal = true;
          }
        }
        
        setInput(currentTranscript); // Type it in the chat box

        if (isFinal && currentTranscript.trim().length > 0) {
           const msg = currentTranscript;
           setInput('');
           setIsListening(false);
           
           if (latestSessionId.current) {
             setMessages(prev => [...prev, { role: 'user', content: msg }]);
             addAuditLog(`User voice message received`, 'action');
             latestExecuteChat.current(msg);
           }
        }
      };

      recognitionRef.current.onerror = (event: any) => {
        console.error('Speech recognition error', event.error);
        if (event.error === 'not-allowed') {
          alert("Microphone access was denied! Please allow microphone access in your browser URL bar settings and try again.");
        } else if (event.error !== 'no-speech') {
          alert("Microphone error: " + event.error);
        }
        setIsListening(false);
      };
      
      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert("Microphone is not supported in this browser, or you are not using a Secure Context (HTTPS/localhost). Please use Google Chrome.");
      return;
    }
    
    if (isListening) {
      try {
        recognitionRef.current.stop();
      } catch (e) {
        console.error(e);
      }
      setIsListening(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch (e: any) {
        console.error(e);
        alert("Failed to start microphone: " + e.message + "\n\nPlease ensure you have granted microphone permissions.");
        setIsListening(false);
      }
    }
  };

  const handleActionMessage = async (msg: string) => {
    if (!sessionId) return;
    setMessages(prev => [...prev, { role: 'user', content: msg }]);
    addAuditLog(`User selected an action`, 'action');
    await executeChat(msg);
  }

  const sendMessage = async () => {
    if (!input.trim() || !sessionId) return;
    const msg = input;
    setInput('')
    
    setMessages(prev => [...prev, { role: 'user', content: msg }])
    addAuditLog(`User message received`, 'action');
    await executeChat(msg);
  }
  
  async function executeChat(messageText: string) {
    setIsThinking(true);
    try {
      const res = await fetch(`http://localhost:8000/v1/chat/${sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: messageText })
      })
      
      const data = await res.json()
      
      setMessages(prev => [...prev, {
        role: 'assistant', 
        content: data.content + (data.data?.payment_link_url ? `\n\nFallback Payment Link: ${data.data.payment_link_url}` : ''),
        action: data.action,
        data: data.data
      }])
      
      if (data.data?.upsell_message) {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.data.upsell_message
        }]);
      }
      
      if (data.decision === "approved") {
         addAuditLog(`Action approved: ${data.action || 'chat'}`, 'success');
      } else if (data.decision === "gated_pending") {
         addAuditLog(`Action gated (pending confirmation)`, 'neutral');
      }
      
      if (data.data?.order_id && data.data?.razorpay_key_id) {
          addAuditLog(`Checkout initiated (${data.data.order_id})`, 'action');
          
          const options = {
              "key": data.data.razorpay_key_id,
              "amount": data.data.amount_paise,
              "currency": "INR",
              "name": "Growth Agent Store",
              "description": "Agent Checkout",
              "order_id": data.data.order_id,
              "handler": function (response: any) {
                  addAuditLog(`Payment successful: ${response.razorpay_payment_id}`, 'success');
                  setOrdersCount(prev => prev + 1);
                  setRevenue(prev => prev + Math.floor(data.data.amount_paise / 100));
                  setMessages(prev => [...prev, {
                      role: 'assistant', 
                      content: `Payment Successful! 🎉\nPayment ID: ${response.razorpay_payment_id}\n\nThe backend webhook is now securely recording this in the audit log.`
                  }]);
              },
              "theme": { "color": "#1E1D1A" }
          };
          const rzp1 = new (window as any).Razorpay(options);
          rzp1.on('payment.failed', function (response: any){
              addAuditLog(`Payment failed: ${response.error.description}`, 'neutral');
              setMessages(prev => [...prev, {
                  role: 'assistant', 
                  content: `Payment failed or was cancelled. Error: ${response.error.description}`
              }]);
          });
          rzp1.open();
      }
    } catch (e) {
      setMessages(prev => [...prev, {role: 'assistant', content: 'Error communicating with server.'}])
      addAuditLog(`Error communicating with API`, 'neutral');
    } finally {
      setIsThinking(false);
    }
  }

  if (!isAuthenticated) {
    return (
      <motion.div 
        className="auth-page"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8 }}
      >
        {/* BACKGROUND VIDEO */}
        {/* REPLACE THE 'src' URL BELOW WITH YOUR OWN LOCAL OR HOSTED VIDEO PATH */}
        <video 
          className="auth-bg-video" 
          autoPlay 
          loop 
          muted 
          playsInline
          src="h6.mp4" 
        />

        <motion.div 
          className="auth-card"
          initial={{ opacity: 0, scale: 0.95, y: 30 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="auth-left">
            <div>
              <h1>Meera's Store</h1>
              <p className="desc">
                Experience the future of shopping. Our AI agent perfectly understands your style and safely checks you out.
              </p>
            </div>
            <div className="auth-social-proof">
              <div className="avatars">
                <div className="avatar" style={{ backgroundImage: 'url(https://i.pravatar.cc/100?img=12)' }}></div>
                <div className="avatar" style={{ backgroundImage: 'url(https://i.pravatar.cc/100?img=33)' }}></div>
                <div className="avatar" style={{ backgroundImage: 'url(https://i.pravatar.cc/100?img=47)' }}></div>
                <div className="avatar more">+2k</div>
              </div>
              <p className="social-text">Join thousands of premium shoppers today.</p>
            </div>
          </div>
          
          <div className="auth-right">
            <h2>{isSignUp ? 'Create an account' : 'Welcome back'}</h2>
            <p className="subtitle">
              {isSignUp ? 'Please enter your details to sign up.' : 'Please enter your details to sign in.'}
            </p>

            <div className="auth-tabs">
              <button 
                className={`auth-tab ${authMode === 'email' ? 'active' : ''}`}
                onClick={() => setAuthMode('email')}
              >
                Email
              </button>
              <button 
                className={`auth-tab ${authMode === 'phone' ? 'active' : ''}`}
                onClick={() => setAuthMode('phone')}
              >
                Phone
              </button>
            </div>

            {authError && <div className="auth-error">{authError}</div>}
            
            {authMode === 'email' && (
              <>
                <div className="input-group">
                  <label>Email Address</label>
                  <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="hello@example.com" />
                </div>
                <div className="input-group">
                  <label>Password</label>
                  <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" />
                </div>
                <button className="auth-btn" onClick={handleEmailAuth}>
                  {isSignUp ? 'Sign Up' : 'Sign In'} 
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{marginLeft: '4px'}}><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </button>
              </>
            )}

            {authMode === 'phone' && !otpSent && (
              <>
                <div className="input-group">
                  <label>Phone Number</label>
                  <input type="text" value={phoneNumber} onChange={e => setPhoneNumber(e.target.value)} placeholder="+1 555 000 0000" />
                </div>
                <div id="recaptcha-container"></div>
                <button className="auth-btn" onClick={handlePhoneAuth}>
                  Send OTP 
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{marginLeft: '4px'}}><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </button>
              </>
            )}

            {authMode === 'phone' && otpSent && (
              <>
                <div className="input-group">
                  <label>Enter 6-Digit OTP</label>
                  <input type="text" value={otp} onChange={e => setOtp(e.target.value)} placeholder="123456" />
                </div>
                <button className="auth-btn" onClick={handleVerifyOtp}>
                  Verify OTP 
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{marginLeft: '4px'}}><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                </button>
              </>
            )}

            <div className="auth-divider">OR</div>

            <button className="auth-google-btn" onClick={handleGoogleSignIn}>
              <svg width="20" height="20" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
              </svg>
              Continue with Google
            </button>
            
            <p className="auth-switch">
              {isSignUp ? 'Already have an account? ' : "Don't have an account? "}
              <span onClick={() => setIsSignUp(!isSignUp)}>
                {isSignUp ? 'Sign in' : 'Sign up'}
              </span>
            </p>
          </div>
        </motion.div>
      </motion.div>
    );
  }

  const containerVariants: any = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.15 } }
  };

  const itemVariants: any = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } }
  };

  return (
    <div className="dashboard-container">
      {/* Top Bar */}
      <motion.div 
        className="top-bar"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
      >
        <div className="top-bar-left">
          <h1>Agent Overview</h1>
          <div className="tabs">
            <button className={activeTab === 'dashboard' ? 'active' : ''} onClick={() => setActiveTab('dashboard')}>Dashboard</button>
            <button className={activeTab === 'inventory' ? 'active' : ''} onClick={() => setActiveTab('inventory')}>Inventory</button>
            <button className={activeTab === 'settings' ? 'active' : ''} onClick={() => setActiveTab('settings')}>Guardrails</button>
          </div>
        </div>
        <div className="top-bar-right">
          <button className="icon-btn">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
          </button>
          <button className="sign-out-btn" onClick={() => setIsAuthenticated(false)}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
            Logout
          </button>
        </div>
      </motion.div>

      {/* Dashboard View */}
      {activeTab === 'dashboard' && (
        <motion.div 
          className="main-grid"
          variants={containerVariants}
          initial="hidden"
          animate="show"
        >
          {/* ... ledger, chat, audit log ... */}
          {/* LEFT: Ledger */}
          <motion.div className="card" variants={itemVariants}>
            <div className="card-header">
              <h2><span className="dot"></span> Today's Ledger</h2>
            </div>
            <div className="ledger-stats">
              <div className="stat-row">
                <span>Sessions</span>
                <div className="stat-value"><AnimatedNumber value={sessionsCount} /></div>
              </div>
              <div className="stat-row">
                <span>Orders</span>
                <div className="stat-value"><AnimatedNumber value={ordersCount} /></div>
              </div>
              <div className="stat-row">
                <span>Upsells</span>
                <div className="stat-value" style={{color: '#10B981'}}>+₹<AnimatedNumber value={2400} /></div>
              </div>
              <div className="revenue-box">
                <span>Revenue</span>
                <div className="rev-amount"><AnimatedNumber value={revenue} prefix="₹" /></div>
              </div>
            </div>
            
            <div className="chart-container" style={{ height: '180px', marginTop: '10px', padding: '0 24px', marginBottom: '30px' }}>
              <h4 style={{ fontSize: '12px', color: '#9CA3AF', marginBottom: '10px', textTransform: 'uppercase' }}>Revenue 24H</h4>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 15, left: 15, bottom: 5 }}>
                  <XAxis dataKey="time" stroke="#9CA3AF" fontSize={10} tickLine={false} axisLine={false} />
                  <Tooltip 
                    contentStyle={{ background: '#111', border: 'none', borderRadius: '4px', color: '#fff', fontSize: '12px' }}
                    itemStyle={{ color: '#fff' }}
                  />
                  <Line type="monotone" dataKey="rev" stroke="#3b82f6" strokeWidth={3} dot={false} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </motion.div>

          {/* CENTER: Chat */}
          <motion.div className="card chat-card" variants={itemVariants}>
            <div className="card-header">
              <h2>Meera's Store Agent</h2>
            </div>
            <div className="chat-messages">
              <AnimatePresence initial={false}>
                {messages.map((m, i) => (
                  <motion.div 
                    key={i} 
                    className="message-container"
                    initial={{ opacity: 0, y: 15, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ duration: 0.3, ease: "easeOut" }}
                  >
                    <div className={`message ${m.role}`}>
                      {m.content}
                    </div>
                    
                    {/* Rich Product UI */}
                    {m.action === 'search_catalog' && Array.isArray(m.data) && (
                      <div className="product-carousel">
                          {m.data.map((p, pIdx) => (
                            <ProductCard 
                              key={pIdx} 
                              p={p} 
                              pIdx={pIdx} 
                              handleActionMessage={handleActionMessage} 
                            />
                          ))}
                      </div>
                    )}
                    
                    {/* Rich Cart UI */}
                    {m.action === 'add_to_cart' && m.data && m.data.items && (
                      <motion.div 
                        className="cart-card"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                      >
                        <h3>Confirm your order</h3>
                        {m.data.items.map((item: any, cIdx: number) => (
                          <div className="cart-item" key={cIdx}>
                            <span>{item.qty}× {item.title}</span>
                            <span>₹{Math.floor(item.price_paise / 100)}</span>
                          </div>
                        ))}
                        <div className="cart-total">
                          <span>Total</span>
                          <span>₹{Math.floor(m.data.total_paise / 100)}</span>
                        </div>
                        <button onClick={() => handleActionMessage(`checkout`)}>
                          Confirm & Pay 
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                        </button>
                      </motion.div>
                    )}
                    
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
            <div className="chat-input-wrapper">
              <input 
                value={input} 
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && sendMessage()}
                placeholder={isListening ? "Listening..." : (isThinking ? "Thinking..." : "Type a message...")}
                disabled={isThinking}
              />
              <button className={`mic-btn ${isListening ? 'listening' : ''}`} onClick={toggleListening} title="Voice Command">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                  <line x1="12" y1="19" x2="12" y2="22"></line>
                </svg>
              </button>
              <button onClick={sendMessage} className="send-btn">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
              </button>
            </div>
          </motion.div>

          {/* RIGHT: Audit Log */}
          <motion.div className="card" variants={itemVariants}>
            <div className="card-header">
              <div className="audit-header-content">
                <h2>Audit Log</h2>
                <div className="session-badge">{sessionId ? `sess_${sessionId.substring(0,4)}` : ''}</div>
              </div>
            </div>
            <div className="audit-timeline">
              <AnimatePresence initial={false}>
                {auditLogs.map((log, index) => (
                  <motion.div 
                    className="timeline-item" 
                    key={index}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.4, ease: "easeOut" }}
                  >
                    <div className={`timeline-dot ${log.type}`}></div>
                    <div className="timeline-content">
                      <div className="timeline-time">{log.time}</div>
                      <div className="timeline-text">{log.text}</div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </motion.div>

        </motion.div>
      )}

      {/* Inventory View */}
      {activeTab === 'inventory' && <InventoryTab />}

      {/* Settings View */}
      {activeTab === 'settings' && <SettingsTab />}
    </div>
  )
}

export default App
