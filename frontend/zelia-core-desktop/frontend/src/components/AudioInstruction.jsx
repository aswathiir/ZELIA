import React, { useEffect, useState } from 'react';
import { Volume2, Loader, Play } from 'lucide-react';
import { speak, stopSpeech } from '../utils/speechHelper';
import { useLanguage } from '../context/LanguageContext';

export const AudioInstruction = ({ text, enText }) => {
    const { langCode } = useLanguage();
    const [isPlaying, setIsPlaying] = useState(false);

    const playAudio = () => {
        setIsPlaying(true);
        speak(text, langCode, () => setIsPlaying(false), enText);
    };

    useEffect(() => {
        // Auto-play on mount
        const timer = setTimeout(() => {
            playAudio();
        }, 500); // Slight delay for smoother UX

        return () => {
            clearTimeout(timer);
            stopSpeech();
        };
    }, [text, langCode]);

    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: 24,
            width: '100%'
        }}>
            <button
                onClick={playAudio}
                disabled={isPlaying}
                style={{
                    background: isPlaying ? '#EAF0F7' : '#FFFFFF',
                    border: '2px solid #C0D0E0',
                    borderRadius: 30,
                    padding: '12px 24px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    cursor: isPlaying ? 'default' : 'pointer',
                    color: '#0D1B33',
                    fontSize: 16,
                    fontWeight: 800,
                    boxShadow: '0 4px 12px rgba(6,14,31,0.08)',
                    transition: 'all 0.2s',
                    fontFamily: 'inherit'
                }}
            >
                {isPlaying ? (
                    <>
                        <Volume2 size={24} color="#1A5C3A" style={{ animation: 'pulse 1.5s infinite' }} />
                        <span style={{ color: '#1A5C3A' }}>Speaking...</span>
                    </>
                ) : (
                    <>
                        <Play size={24} color="#0D1B33" />
                        <span>Listen Again</span>
                    </>
                )}
            </button>

            <style>{`
                @keyframes pulse {
                    0% { transform: scale(1); opacity: 1; }
                    50% { transform: scale(1.1); opacity: 0.7; }
                    100% { transform: scale(1); opacity: 1; }
                }
            `}</style>
        </div>
    );
};
