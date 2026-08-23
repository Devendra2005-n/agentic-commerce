import React, { useState, useRef } from 'react';
import gsap from 'gsap';
import { useGSAP } from '@gsap/react';

export default function EmbeddedChat({ onTimelineUpdate, globalUser }: { onTimelineUpdate: (ev: any) => void, globalUser: string }) {
  const chatRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [messages, setMessages] = useState<any[]>([
    { type: 'system', text: "?? Hi! I can help you find something from Meera's Store. What are you looking for?" }
  ]);
  const [input, setInput] = useState('');
  const [expandedReason, setExpandedReason] = useState<number | null>(null);

  const sendTextToAgent = async (userMsg: string) => {
    if (!userMsg.trim()) return;

    setMessages(prev => [...prev, { type: 'user', text: userMsg }]);
    
    // Log user input to timeline
    onTimelineUpdate({ desc: "Buyer said: \"\"", type: 'info' });

    try {
      const response = await fetch('https://agentic-commerce-qgvc.onrender.com/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, buyer_ref: globalUser })
      });
      const data = await response.json();
      setMessages(prev => [...prev, { type: data.type, text: data.text, payload: data }]);
      
      // Update Dashboard Timeline dynamically based on agent action!
      if (data.type === 'catalog_results') {
        onTimelineUpdate({ desc: 'Catalog search executed', type: 'check', checks: ['? sku_exists', '? price_matches'] });
      } else if (data.type === 'upsell_prompt') {
        onTimelineUpdate({ desc: "Upsell proposed", type: 'check', reason: data.reason_rendered, checks: ['? upsell_attempt_cap', "? reason_req'd"] });
      } else if (data.type === 'checkout_confirm') {
        onTimelineUpdate({ desc: 'Checkout verified by Guardrail', type: 'check', checks: ['? order_ceiling'] });
      } else if (data.type === 'payment_success') {
        onTimelineUpdate({ desc: 'Webhook: payment.captured ? verified', type: 'success' });
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

  useGSAP(() => {
    if (chatRef.current) {
      gsap.fromTo(chatRef.current, 
        { y: 50, opacity: 0 }, 
        { y: 0, opacity: 1, duration: 0.6, ease: "back.out(1.7)", delay: 0.2 }
      );
    }
  }, []);

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

  return (
    <div ref={chatRef} className="flex flex-col h-[600px] bg-paper border border-ink-faint/20 rounded-2xl shadow-sm overflow-hidden">
      
      {/* Header */}
      <div className="bg-gradient-to-r from-ink to-[#2a2925] text-white p-4 flex justify-between items-center shadow-md z-10 relative">
        <h3 className="font-display text-lg tracking-wide">Meera's Store Agent</h3>
      </div>

      {/* Messages Area */}
      <div className="flex-1 p-4 overflow-y-auto space-y-6 bg-paper relative">
        {messages.map((msg, idx) => (
          <div key={idx} className={"message-bubble flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}"}>
            
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
                    <span className="text-ledger-blue mt-0.5">?</span>
                    <p>{msg.text}</p>
                  </div>
                )}

                {/* Catalog Search Results */}
                {msg.type === 'catalog_results' && (
                  <div className="space-y-3">
                    <div className="flex items-start gap-2 bg-white/60 p-3 rounded-xl border border-ink-faint/10 shadow-sm mb-2">
                       <span className="text-ledger-blue mt-0.5">?</span>
                       <p>{msg.text}</p>
                    </div>
                    
                    <div className="flex gap-3 overflow-x-auto pb-2 px-1">
                      {msg.payload.results.map((product: any, pIdx: number) => (
                        <div key={pIdx} className="bg-white border border-ink-faint/20 rounded-xl p-3 shadow-sm min-w-[160px] flex-shrink-0 group hover:shadow-md transition-shadow">
                          <div className="h-24 bg-paper rounded-lg mb-3 overflow-hidden">
                            <img src={product.img} alt={product.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                          </div>
                          <p className="font-medium text-sm line-clamp-1">{product.title}</p>
                          <p className="text-ledger-blue font-semibold mt-1">?{product.price}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Upsell Prompt */}
                {msg.type === 'upsell_prompt' && (
                  <div className="bg-[#F5F9FF] border border-[#D0E2FF] rounded-xl p-4 shadow-sm relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-24 h-24 bg-[#E5EFFF] rounded-bl-full -mr-4 -mt-4"></div>
                    
                    <div className="flex items-start gap-2 mb-4 relative z-10">
                      <span className="text-[#0F62FE] mt-0.5">??</span>
                      <p className="text-[#001D6C] font-medium">{msg.text}</p>
                    </div>

                    <div className="bg-white p-3 rounded-lg flex items-center gap-4 relative z-10 border border-[#D0E2FF]/50">
                      <div className="h-16 w-16 bg-paper rounded overflow-hidden shrink-0">
                         <img src={msg.payload.upsell_item.img} alt={msg.payload.upsell_item.title} className="w-full h-full object-cover" />
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-sm">{msg.payload.upsell_item.title}</p>
                        <p className="text-[#0F62FE] font-bold mt-0.5">?{msg.payload.upsell_item.price}</p>
                      </div>
                      <button className="bg-[#0F62FE] text-white px-3 py-1.5 rounded text-sm font-medium hover:bg-[#003A6D] transition-colors">
                        Add to Order
                      </button>
                    </div>

                    {/* Explainer tag */}
                    <button 
                      onClick={() => setExpandedReason(expandedReason === idx ? null : idx)}
                      className="mt-3 text-xs text-[#0F62FE] flex items-center gap-1 font-medium hover:underline relative z-10"
                    >
                      Why am I seeing this?
                      <svg className={"w-3 h-3 transition-transform ${expandedReason === idx ? 'rotate-180' : ''}"} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                    </button>
                    
                    {expandedReason === idx && (
                      <div className="mt-2 text-xs bg-white/60 p-2 rounded border border-[#D0E2FF]/50 text-[#001D6C]/70 relative z-10">
                        {msg.payload.reason_rendered}
                      </div>
                    )}
                  </div>
                )}

                {/* Checkout Cart & Razorpay trigger */}
                {msg.type === 'checkout_confirm' && (
                  <div className="bg-white border-2 border-ledger-amber rounded-xl p-4 shadow-md">
                    <div className="flex items-start gap-2 mb-4">
                      <span className="text-ledger-amber mt-0.5">??</span>
                      <p className="font-medium">{msg.text}</p>
                    </div>

                    <div className="bg-paper p-3 rounded-lg mb-4 space-y-2">
                      {msg.payload.cart.map((item: any, cIdx: number) => (
                        <div key={cIdx} className="flex justify-between items-center text-sm">
                          <span className="text-ink/80">{item.title}</span>
                          <span className="font-semibold">?{item.price}</span>
                        </div>
                      ))}
                      <div className="border-t border-ink-faint/20 pt-2 mt-2 flex justify-between items-center font-bold">
                        <span>Total:</span>
                        <span>?{msg.payload.total}</span>
                      </div>
                    </div>

                    <button 
                      onClick={async () => {
                        // Demo UI trigger for Razorpay using Hackathon test keys
                        const options = {
                          key: "rzp_test_5gT9B2hK0L9M6n",
                          amount: msg.payload.total * 100,
                          currency: "INR",
                          name: "Meera's Store",
                          description: "Agentic Checkout Demo",
                          handler: async function (response: any) {
                            await sendTextToAgent("payment_successful_callback_id_");
                          },
                          theme: { color: "#2B4570" }
                        };
                        const rzp = new (window as any).Razorpay(options);
                        rzp.open();
                      }}
                      className="w-full bg-ledger-amber hover:bg-ledger-amber/90 text-white font-bold py-3 rounded-lg transition-colors flex justify-center items-center gap-2 shadow-sm"
                    >
                      Confirm & Pay Securely
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                    </button>
                  </div>
                )}
                
                {/* Payment Success Receipt */}
                {msg.type === 'payment_success' && (
                  <div className="bg-[#F2FAF5] border border-[#A6E3B9] rounded-xl p-4 shadow-sm">
                    <div className="flex items-start gap-2 mb-2">
                      <div className="w-6 h-6 rounded-full bg-ledger-green flex items-center justify-center shrink-0">
                        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
                      </div>
                      <p className="text-[#1A5331] font-medium">{msg.text}</p>
                    </div>
                  </div>
                )}

              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
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


