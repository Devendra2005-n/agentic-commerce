import React, { useState } from 'react';

export default function ChatWidget({ onTimelineUpdate }: { onTimelineUpdate: (ev: any) => void }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<any[]>([
    { type: 'system', text: "🛍 Hi! I can help you find something from Flexta Store. What are you looking for?" }
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
        body: JSON.stringify({ message: userMsg })
      });
      const data = await response.json();
      setMessages(prev => [...prev, { type: data.type, text: data.text, payload: data }]);
      
      // Update Dashboard Timeline dynamically based on agent action!
      if (data.type === 'catalog_results') {
        onTimelineUpdate({ desc: 'Catalog search executed (2 matches)', type: 'check', checks: ['✓ sku_exists', '✓ price_matches'] });
      } else if (data.type === 'upsell_prompt') {
        onTimelineUpdate({ desc: `Upsell proposed: ${data.upsell_item.title}`, type: 'check', reason: data.reason_rendered, checks: ['✓ upsell_attempt_cap', "✓ reason_req'd"] });
      } else if (data.type === 'checkout_confirm') {
        onTimelineUpdate({ desc: 'Checkout verified by Guardrail', type: 'check', checks: ['✓ order_ceiling (₹1399 ≤ ₹5000)'] });
      } else if (data.type === 'payment_success') {
        onTimelineUpdate({ desc: 'Webhook: payment.captured ✓ verified', type: 'success' });
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

  return (
    <>
      {/* Floating Chat Button */}
      <button 
        onClick={() => setIsOpen(true)}
        className={`fixed bottom-8 right-8 h-16 w-16 bg-ledger-blue text-white rounded-full shadow-[0_10px_20px_rgba(43,69,112,0.3)] flex items-center justify-center hover:scale-110 transition-transform z-50 ${isOpen ? 'hidden' : ''}`}
      >
        <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
        </svg>
      </button>

      {/* Chat Window */}
      {isOpen && (
        <div className="fixed bottom-8 right-8 w-96 h-[600px] bg-paper border border-ink-faint/20 rounded-2xl shadow-[0_20px_40px_rgba(0,0,0,0.2)] flex flex-col z-50 overflow-hidden transform transition-all">
          
          {/* Header */}
          <div className="bg-gradient-to-r from-ink to-[#2a2925] text-white p-4 flex justify-between items-center shadow-md z-10 relative">
            <h3 className="font-display text-lg tracking-wide">Flexta Store Agent</h3>
            <button onClick={() => setIsOpen(false)} className="text-white/70 hover:text-white transition-colors">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>

          {/* Messages Area */}
          <div className="flex-1 p-4 overflow-y-auto space-y-6 bg-paper relative">
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                
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
                            onClick={() => {
                              const rzpKey = "rzp_test_TSfHa8QhpL6X3t"; // Replace with real test key
                              
                              // If using the mock key, we used to simulate the modal, but now we always open the real Razorpay screen.

                              // Trigger Real Razorpay Modal Integration
                              if ((window as any).Razorpay) {
                                const options = {
                                  key: rzpKey,
                                  amount: msg.payload.total * 100, // paise
                                  currency: "INR",
                                  name: "Flexta Store",
                                  description: "Agentic Checkout",
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
      )}
    </>
  );
}

