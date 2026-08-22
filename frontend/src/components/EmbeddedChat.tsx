import React, { useState, useRef } from 'react';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';

export default function EmbeddedChat({ onTimelineUpdate }: { onTimelineUpdate: (ev: any) => void }) {
  const [phoneNumber, setPhoneNumber] = useState('');
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const loginRef = useRef<HTMLDivElement>(null);
  const chatRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [messages, setMessages] = useState<any[]>([
    { type: 'system', text: "👋 Hi! I can help you find something from Meera's store. What are you looking for?" }
  ]);
  const [input, setInput] = useState('');
  const [expandedReason, setExpandedReason] = useState<number | null>(null);

  const sendTextToAgent = async (userMsg: string) => {
    if (!userMsg.trim()) return;

    setMessages(prev => [...prev, { type: 'user', text: userMsg }]);
    
    // Log user input to timeline
    onTimelineUpdate({ desc: `Buyer said: "${userMsg}"`, type: 'info' });

    try {
      const response = await fetch('https://agentic-commerce-qgvc.onrender.com/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, buyer_ref: phoneNumber })
      });
      const data = await response.json();
      setMessages(prev => [...prev, { type: data.type, text: data.text, payload: data }]);
      
      // Update Dashboard Timeline dynamically based on agent action!
      if (data.type === 'catalog_results') {
        onTimelineUpdate({ desc: 'Catalog search executed', type: 'check', checks: ['✅ sku_exists', '✅ price_matches'] });
      } else if (data.type === 'upsell_prompt') {
        onTimelineUpdate({ desc: `Upsell proposed`, type: 'check', reason: data.reason_rendered, checks: ['✅ upsell_attempt_cap', "✅ reason_req'd"] });
      } else if (data.type === 'checkout_confirm') {
        onTimelineUpdate({ desc: 'Checkout verified by Guardrail', type: 'check', checks: ['✅ order_ceiling'] });
      } else if (data.type === 'payment_success') {
        onTimelineUpdate({ desc: 'Webhook: payment.captured ✅ verified', type: 'success' });
      }
      
    } catch (err) {
      setMessages(prev => [...prev, { type: 'system', text: 'Error connecting to the agent. Make sure the backend is running!' }]);
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    const currentInput = input;
    setInput('');
    await sendTextToAgent(currentInput);
  };

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (phoneNumber.trim().length > 5) {
      gsap.to(loginRef.current, { 
        scale: 0.9, 
        opacity: 0, 
        duration: 0.4, 
        ease: "power2.inOut",
        onComplete: () => {
          setIsLoggedIn(true);
        }
      });
    }
  };

  useGSAP(() => {
    if (isLoggedIn && chatRef.current) {
      gsap.fromTo(chatRef.current, 
        { y: 50, opacity: 0 }, 
        { y: 0, opacity: 1, duration: 0.6, ease: "back.out(1.7)" }
      );
    }
  }, [isLoggedIn]);

  useGSAP(() => {
    // Animate new messages
    gsap.fromTo(".message-bubble:last-child",
      { scale: 0.8, opacity: 0, y: 10 },
      { scale: 1, opacity: 1, y: 0, duration: 0.4, ease: "back.out(1.5)", transformOrigin: "bottom left" }
    );
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  if (!isLoggedIn) {
    return (
      <div ref={loginRef} className="h-[600px] flex flex-col items-center justify-center bg-gray-50 p-6 border border-gray-200 rounded-2xl shadow-sm">
        <div className="bg-white p-8 rounded-xl shadow-md text-center max-w-sm w-full">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Login Securely</h2>
          <p className="text-gray-500 mb-6 text-sm">Enter your phone number to access your personalized AI agent.</p>
          <form onSubmit={handleLogin}>
            <input 
              type="tel" 
              placeholder="+1 (555) 000-0000" 
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all mb-4 outline-none text-center text-lg"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              required
            />
            <button type="submit" className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors shadow-sm">
              Secure Login
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div ref={chatRef} className="flex flex-col h-[600px] bg-paper border border-ink-faint/20 rounded-2xl shadow-sm overflow-hidden">
      
      {/* Header */}
      <div className="bg-gradient-to-r from-ink to-[#2a2925] text-white p-4 flex justify-between items-center shadow-md z-10 relative">
        <h3 className="font-display text-lg tracking-wide">Meera's Store Agent</h3>
      </div>

      {/* Messages Area */}
      <div className="flex-1 p-4 overflow-y-auto space-y-6 bg-paper relative">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message-bubble flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
            
            {/* User Bubble */}
            {msg.type === 'user' && (
              <div className="bg-ink text-paper px-4 py-2.5 rounded-2xl rounded-tr-sm max-w-[80%] shadow-sm">
                {msg.text}
              </div>
            )}

            {/* Agent Responses */}
            {msg.type !== 'user' && (
              <div className="max-w-[95%] text-ink">
                {/* Standard Text */}
                {(msg.type === 'system' || msg.type === 'text') && (
                  <div className="flex items-start gap-2 bg-white/60 p-3 rounded-xl border border-ink-faint/10 shadow-sm">
                    <span className="text-ledger-blue mt-0.5">✦</span>
                    <p>{msg.text}</p>
                  </div>
                )}

                {/* Interactive Catalog Cards */}
                {msg.type === 'catalog_results' && (
                  <div className="mt-2">
                    <div className="flex items-start gap-2 bg-white/60 p-3 rounded-xl border border-ink-faint/10 shadow-sm mb-3">
                       <span className="text-ledger-blue mt-0.5">✦</span>
                       <p>{msg.text}</p>
                    </div>
                    <div className="flex gap-3 overflow-x-auto pb-2 pl-2 snap-x">
                      {msg.payload.results.map((item: any, i: number) => (
                        <div key={i} className="min-w-[150px] snap-center bg-white border border-ink-faint/15 rounded-xl p-3 shadow-sm hover:shadow-md transition-all hover:-translate-y-1">
                          <div className="h-24 bg-ink-faint/5 rounded-lg mb-3 overflow-hidden">
                            {item.img ? (
                              <img src={item.img} alt={item.title} className="w-full h-full object-cover mix-blend-multiply" />
                            ) : (
                              <div className="w-full h-full flex items-center justify-center text-xs text-ink-faint font-medium">Image</div>
                            )}
                          </div>
                          <p className="font-semibold text-ink leading-tight">{item.title}</p>
                          <p className="money text-ledger-blue font-medium mt-1">₹{item.price}</p>
                          <button 
                            onClick={() => sendTextToAgent(`checkout ${item.title}`)}
                            className="w-full mt-3 bg-ledger-blue/10 hover:bg-ledger-blue text-ledger-blue hover:text-white transition-colors text-sm font-medium py-2 rounded-lg"
                          >
                            Select
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Upsell Prompt */}
                {msg.type === 'upsell_prompt' && (
                  <div className="mt-2 bg-white border border-ledger-amber/30 rounded-xl overflow-hidden shadow-sm">
                    <div className="bg-ledger-amber/10 px-4 py-2 flex items-center gap-2 border-b border-ledger-amber/20">
                      <span className="text-ledger-amber text-lg">💡</span>
                      <span className="font-medium text-ledger-amber">Frequently bought together</span>
                    </div>
                    <div className="p-4">
                      <p className="mb-3 text-ink/90">{msg.text}</p>
                      <div className="flex gap-3 items-center bg-paper p-2 rounded-lg mb-4">
                        <div className="w-12 h-12 bg-white rounded flex-shrink-0 overflow-hidden border border-ink-faint/10 shadow-sm">
                           {msg.payload.upsell_item.img && <img src={msg.payload.upsell_item.img} className="w-full h-full object-cover mix-blend-multiply" alt="upsell item" />}
                        </div>
                        <div>
                          <p className="font-medium text-sm">{msg.payload.upsell_item.title}</p>
                          <p className="money text-ledger-blue text-sm font-semibold">₹{msg.payload.upsell_item.price}</p>
                        </div>
                      </div>
                      
                      <button 
                        onClick={() => setExpandedReason(expandedReason === idx ? null : idx)}
                        className="text-xs font-medium text-ink-faint hover:text-ink underline decoration-ink-faint/30 underline-offset-2 mb-4 transition-colors"
                      >
                        Why am I seeing this?
                      </button>
                      
                      {expandedReason === idx && (
                        <div className="bg-highlight p-3 rounded-lg mb-4 text-sm code-value text-ink border border-ink-faint/20 shadow-inner">
                          {msg.payload.reason_rendered}
                        </div>
                      )}

                      <div className="flex gap-2">
                        <button onClick={() => sendTextToAgent(`no thanks, just checkout`)} className="flex-1 py-2 text-sm font-medium text-ink border border-ink-faint/20 rounded-lg hover:bg-paper transition-colors">
                          No thanks
                        </button>
                        <button onClick={() => sendTextToAgent(`add ${msg.payload.upsell_item.title}`)} className="flex-1 py-2 text-sm font-medium text-white bg-ledger-blue rounded-lg shadow-sm hover:bg-ledger-blue/90 transition-colors">
                          Add for ₹{msg.payload.upsell_item.price}
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Checkout Confirm */}
                {msg.type === 'checkout_confirm' && (
                  <div className="mt-2 bg-white border-2 border-ink-faint/20 rounded-xl overflow-hidden shadow-md">
                    <div className="bg-paper px-4 py-3 border-b border-ink-faint/10">
                      <h4 className="font-display font-medium text-lg text-ink">Confirm your order</h4>
                    </div>
                    <div className="p-4">
                      <div className="space-y-2 mb-4">
                        {msg.payload.cart.map((item: any, i: number) => (
                          <div key={i} className="flex justify-between items-center text-sm">
                            <span>1× {item.title}</span>
                            <span className="money">₹{item.price}</span>
                          </div>
                        ))}
                      </div>
                      <div className="border-t border-dashed border-ink-faint/30 pt-3 mb-5 flex justify-between items-center">
                        <span className="font-medium">Total</span>
                        <span className="money font-semibold text-lg text-ledger-blue">₹{msg.payload.total}</span>
                      </div>
                      
                      <button 
                        onClick={async () => {
                          const rzpKey = "rzp_test_TSfHa8QhpL6X3t";
                          
                          // Trigger Real Razorpay Modal Integration
                          if ((window as any).Razorpay) {
                            try {
                              const res = await fetch('https://agentic-commerce-qgvc.onrender.com/api/orders', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ amount_paise: msg.payload.total * 100 })
                              });
                              const data = await res.json();
                              
                              if (!res.ok) {
                                alert("Failed to create order on backend: " + (data.detail || "Unknown error"));
                                return;
                              }

                              const options = {
                                key: rzpKey,
                                amount: msg.payload.total * 100, // paise
                                currency: "INR",
                                name: "Meera's Store",
                                description: "Agentic Checkout",
                                order_id: data.order_id, // REAL ORDER ID FROM BACKEND!
                                handler: function (response: any) {
                                  sendTextToAgent(`payment_successful_callback_id_${response.razorpay_payment_id}`);
                                },
                                prefill: {
                                  name: "Test Buyer",
                                  email: "test@example.com",
                                  contact: "9999999999"
                                },
                                theme: { color: "#2B4570" } // ledger-blue
                              };
                              const rzp = new (window as any).Razorpay(options);
                              rzp.open();
                            } catch (err) {
                              alert("Failed to communicate with backend to create order.");
                            }
                          } else {
                            sendTextToAgent(`confirm and pay`);
                          }
                        }}
                        className="w-full py-2.5 text-sm font-medium text-white bg-ink rounded-lg shadow-sm hover:bg-black transition-colors flex items-center justify-center gap-2"
                      >
                        Confirm & Pay via Razorpay
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
                      </button>
                    </div>
                  </div>
                )}

                {/* Payment Success */}
                {msg.type === 'payment_success' && (
                  <div className="mt-2 bg-[#F3FAF5] border border-[#BDE3C8] p-4 rounded-xl shadow-sm">
                    <div className="flex items-center gap-3 text-[#2D7344] mb-2">
                       <div className="w-8 h-8 rounded-full bg-[#2D7344] text-white flex items-center justify-center">
                         <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" /></svg>
                       </div>
                       <span className="font-medium text-lg">Payment Successful</span>
                    </div>
                    <p className="text-ink/80 text-sm leading-relaxed">{msg.text}</p>
                  </div>
                )}

              </div>
            )}
          </div>
        ))}
      </div>

      {/* Input Area */}
      <form onSubmit={sendMessage} className="p-4 bg-white border-t border-ink-faint/10 z-10 shadow-[0_-10px_20px_rgba(0,0,0,0.02)]">
        <div className="flex gap-2">
          <input 
            type="text" 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..." 
            className="flex-1 bg-paper border border-ink-faint/20 rounded-xl px-4 py-2.5 outline-none focus:border-ledger-blue focus:ring-2 focus:ring-ledger-blue/20 transition-all font-body text-sm"
          />
          <button type="submit" disabled={!input.trim()} className="bg-ledger-blue disabled:opacity-50 text-white w-11 h-11 rounded-xl flex items-center justify-center shadow-sm hover:shadow transition-all hover:-translate-y-0.5">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
          </button>
        </div>
      </form>

    </div>
  );
}



