import React, { useState, useRef } from 'react';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';
import { auth, googleProvider } from '../firebase';
import { signInWithPopup, signInWithEmailAndPassword, createUserWithEmailAndPassword } from 'firebase/auth';

export default function AuthScreen({ onAuthSuccess }: { onAuthSuccess: (user: string) => void }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  
  const containerRef = useRef<HTMLDivElement>(null);
  const formRef = useRef<HTMLDivElement>(null);
  const leftPanelRef = useRef<HTMLDivElement>(null);

  // Initial load animation
  useGSAP(() => {
    gsap.from(containerRef.current, { opacity: 0, scale: 0.95, duration: 1.2, ease: "power3.out" });
    gsap.from(leftPanelRef.current, { x: -50, opacity: 0, duration: 1, delay: 0.3, ease: "power3.out" });
    gsap.from(formRef.current, { y: 30, opacity: 0, duration: 1, delay: 0.5, ease: "power3.out" });
  }, []);

  const toggleMode = () => {
    gsap.to(formRef.current, {
      opacity: 0,
      y: 20,
      duration: 0.3,
      onComplete: () => {
        setIsLogin(!isLogin);
        setError('');
        gsap.fromTo(formRef.current, 
          { opacity: 0, y: -20 },
          { opacity: 1, y: 0, duration: 0.4, ease: "back.out(1.5)" }
        );
      }
    });
  };

  const handleSuccess = (idToken: string) => {
    gsap.to(containerRef.current, {
      scale: 1.1,
      opacity: 0,
      duration: 0.8,
      ease: "power3.inOut",
      onComplete: () => {
        onAuthSuccess(idToken);
      }
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      if (isLogin) {
        const result = await signInWithEmailAndPassword(auth, email, password);
        const token = await result.user.getIdToken();
        handleSuccess(token);
      } else {
        const result = await createUserWithEmailAndPassword(auth, email, password);
        const token = await result.user.getIdToken();
        handleSuccess(token);
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleGoogleLogin = async () => {
    try {
      const result = await signInWithPopup(auth, googleProvider);
      const token = await result.user.getIdToken();
      handleSuccess(token);
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="min-h-screen relative flex items-center justify-center p-4 md:p-12 overflow-hidden selection:bg-ledger-blue/20">
      
      {/* FULL SCREEN VIDEO BACKGROUND */}
      <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover z-0">
        <source src="https://assets.mixkit.co/videos/preview/mixkit-girl-in-a-fashion-store-looking-at-clothes-4980-large.mp4" type="video/mp4" />
      </video>
      {/* Dark overlay for contrast */}
      <div className="absolute inset-0 bg-ink/60 z-0 backdrop-blur-sm"></div>

      <div ref={containerRef} className="max-w-6xl w-full relative z-10 flex flex-col md:flex-row items-center justify-between gap-12">
        
        {/* Left Side - E-commerce Branding (Floating over video) */}
        <div ref={leftPanelRef} className="md:w-5/12 text-white flex flex-col justify-center">
          <h1 className="font-display text-5xl md:text-6xl font-bold tracking-tight mb-6 drop-shadow-lg">Meera's Store</h1>
          <p className="text-gray-200 font-body text-xl leading-relaxed drop-shadow-md mb-12">
            Experience the future of shopping. Our AI agent perfectly understands your style and safely checks you out.
          </p>

          <div className="flex -space-x-4 mb-4">
            <div className="w-14 h-14 rounded-full border-2 border-ink bg-gray-200 bg-[url('https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&q=80')] bg-cover shadow-lg"></div>
            <div className="w-14 h-14 rounded-full border-2 border-ink bg-gray-200 bg-[url('https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=100&q=80')] bg-cover shadow-lg"></div>
            <div className="w-14 h-14 rounded-full border-2 border-ink bg-gray-200 bg-[url('https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&q=80')] bg-cover shadow-lg"></div>
            <div className="w-14 h-14 rounded-full border-2 border-ink bg-ledger-blue flex items-center justify-center text-sm font-bold text-white shadow-lg">+2k</div>
          </div>
          <p className="text-sm font-medium text-gray-300 drop-shadow-sm">Join thousands of premium shoppers today.</p>
        </div>

        {/* Right Side - Glassmorphic Form */}
        <div className="md:w-6/12 max-w-md w-full">
          <div ref={formRef} className="bg-white/95 backdrop-blur-xl p-10 rounded-3xl shadow-[0_20px_60px_-15px_rgba(0,0,0,0.5)] border border-white/20">
            <h2 className="text-3xl font-bold text-ink mb-2">
              {isLogin ? 'Welcome back' : 'Create an account'}
            </h2>
            <p className="text-gray-500 mb-8">
              {isLogin ? 'Please enter your details to sign in.' : 'Enter your details to get started.'}
            </p>

            {error && <div className="mb-6 p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">{error}</div>}

            <button 
              onClick={handleGoogleLogin}
              className="w-full bg-white border border-gray-200 hover:bg-gray-50 text-ink font-medium py-3 rounded-xl transition-colors mb-6 flex items-center justify-center gap-3 shadow-sm"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 24c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 21.53 7.7 24 12 24z"/>
                <path fill="#FBBC05" d="M5.84 15.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V8.06H2.18C1.43 9.55 1 11.22 1 13s.43 3.45 1.18 4.94l3.66-2.84z"/>
                <path fill="#EA4335" d="M12 4.75c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 1.43 14.97 0 12 0 7.7 0 3.99 2.47 2.18 6.06l3.66 2.84c.87-2.6 3.3-4.15 6.16-4.15z"/>
              </svg>
              Continue with Google
            </button>

            <div className="flex items-center gap-4 mb-6">
              <div className="flex-1 h-px bg-gray-200"></div>
              <span className="text-sm text-gray-400 font-medium">OR</span>
              <div className="flex-1 h-px bg-gray-200"></div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              {!isLogin && (
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-ink">Full Name</label>
                  <input 
                    type="text" 
                    placeholder="Jane Doe" 
                    className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-ledger-blue focus:border-ledger-blue outline-none transition-all bg-gray-50 focus:bg-white"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required={!isLogin}
                  />
                </div>
              )}
              
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-ink">Email</label>
                <input 
                  type="email" 
                  placeholder="hello@example.com" 
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-ledger-blue focus:border-ledger-blue outline-none transition-all bg-gray-50 focus:bg-white"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium text-ink">Password</label>
                <input 
                  type="password" 
                  placeholder="••••••••" 
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 focus:ring-2 focus:ring-ledger-blue focus:border-ledger-blue outline-none transition-all bg-gray-50 focus:bg-white"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>

              <button 
                type="submit" 
                className="w-full bg-ink hover:bg-ink/90 text-white font-medium py-3.5 rounded-xl transition-colors shadow-lg shadow-ink/20 flex items-center justify-center gap-2 mt-2"
              >
                {isLogin ? 'Sign In with Email' : 'Create Account'}
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
              </button>
            </form>

            <div className="mt-8 text-center text-sm text-gray-500">
              {isLogin ? "Don't have an account? " : "Already have an account? "}
              <button 
                onClick={toggleMode} 
                className="text-ledger-blue font-semibold hover:underline cursor-pointer"
                type="button"
              >
                {isLogin ? 'Sign up' : 'Log in'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
