import React, { useState, useRef } from 'react';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';

export default function AuthScreen({ onAuthSuccess }: { onAuthSuccess: (user: string) => void }) {
  const [isLogin, setIsLogin] = useState(true);
  const [phone, setPhone] = useState('');
  const [name, setName] = useState('');
  
  const containerRef = useRef<HTMLDivElement>(null);
  const formRef = useRef<HTMLDivElement>(null);
  const leftPanelRef = useRef<HTMLDivElement>(null);

  // Initial load animation
  useGSAP(() => {
    gsap.from(containerRef.current, { opacity: 0, y: 50, duration: 1, ease: "power3.out" });
    gsap.from(leftPanelRef.current, { x: -100, opacity: 0, duration: 1, delay: 0.2, ease: "power3.out" });
    gsap.from(formRef.current, { x: 100, opacity: 0, duration: 1, delay: 0.2, ease: "power3.out" });
  }, []);

  const toggleMode = () => {
    // Animate form out
    gsap.to(formRef.current, {
      opacity: 0,
      y: 20,
      duration: 0.3,
      onComplete: () => {
        setIsLogin(!isLogin);
        // Animate form back in
        gsap.fromTo(formRef.current, 
          { opacity: 0, y: -20 },
          { opacity: 1, y: 0, duration: 0.4, ease: "back.out(1.5)" }
        );
      }
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (phone.length > 5) {
      // Exit animation before notifying parent
      gsap.to(containerRef.current, {
        scale: 0.95,
        opacity: 0,
        duration: 0.6,
        ease: "power3.inOut",
        onComplete: () => {
          onAuthSuccess(phone);
        }
      });
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4 selection:bg-ledger-blue/20">
      <div ref={containerRef} className="max-w-5xl w-full bg-white rounded-3xl shadow-[0_20px_60px_-15px_rgba(0,0,0,0.1)] overflow-hidden flex flex-col md:flex-row min-h-[600px]">
        
        {/* Left Side - E-commerce Branding */}
        <div ref={leftPanelRef} className="md:w-5/12 bg-ink p-12 text-white flex flex-col justify-between relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-ledger-blue/20 to-transparent"></div>
          
          <div className="relative z-10">
            <h1 className="font-display text-4xl font-bold tracking-tight mb-4">Meera's Store</h1>
            <p className="text-gray-300 font-body text-lg leading-relaxed">
              Experience the future of shopping. Our AI agent perfectly understands your style and safely checks you out.
            </p>
          </div>

          <div className="relative z-10 mt-12 md:mt-0">
            <div className="flex -space-x-4 mb-4">
              <div className="w-12 h-12 rounded-full border-2 border-ink bg-gray-200 bg-[url('https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&q=80')] bg-cover"></div>
              <div className="w-12 h-12 rounded-full border-2 border-ink bg-gray-200 bg-[url('https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=100&q=80')] bg-cover"></div>
              <div className="w-12 h-12 rounded-full border-2 border-ink bg-gray-200 bg-[url('https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&q=80')] bg-cover"></div>
              <div className="w-12 h-12 rounded-full border-2 border-ink bg-ledger-blue flex items-center justify-center text-sm font-bold text-white">+2k</div>
            </div>
            <p className="text-sm font-medium text-gray-400">Join thousands of premium shoppers today.</p>
          </div>
        </div>

        {/* Right Side - Form */}
        <div className="md:w-7/12 p-12 flex flex-col justify-center bg-white relative">
          <div ref={formRef} className="max-w-md w-full mx-auto">
            <h2 className="text-3xl font-bold text-ink mb-2">
              {isLogin ? 'Welcome back' : 'Create an account'}
            </h2>
            <p className="text-gray-500 mb-8">
              {isLogin ? 'Please enter your details to sign in.' : 'Enter your details to get started.'}
            </p>

            <form onSubmit={handleSubmit} className="space-y-6">
              {!isLogin && (
                <div className="space-y-2">
                  <label className="text-sm font-medium text-ink">Full Name</label>
                  <input 
                    type="text" 
                    placeholder="Jane Doe" 
                    className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-ledger-blue focus:border-ledger-blue outline-none transition-all bg-gray-50 focus:bg-white"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required={!isLogin}
                  />
                </div>
              )}
              
              <div className="space-y-2">
                <label className="text-sm font-medium text-ink">Phone Number</label>
                <input 
                  type="tel" 
                  placeholder="+1 (555) 000-0000" 
                  className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-ledger-blue focus:border-ledger-blue outline-none transition-all bg-gray-50 focus:bg-white"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  required
                />
              </div>

              <button 
                type="submit" 
                className="w-full bg-ink hover:bg-ink/90 text-white font-medium py-3.5 rounded-lg transition-colors shadow-lg shadow-ink/20 flex items-center justify-center gap-2"
              >
                {isLogin ? 'Sign In' : 'Get Started'}
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