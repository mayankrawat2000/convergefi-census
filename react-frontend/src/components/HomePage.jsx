import { useState } from 'react'
import SearchBox from './SearchBox'

const SUGGESTIONS = [
  { emoji: '⚖️', label: 'Compare Districts',  prompt: 'Show me a comparison of literacy rates in Belgaum vs Bangalore Rural in Karnataka.' },
  { emoji: '📊', label: 'Population Chart',   prompt: 'Show a bar chart comparing population growth rate of Indore, Bhopal, and Jabalpur in Madhya Pradesh.' },
  { emoji: '🔍', label: 'Highest Sex Ratio',  prompt: 'Which district had the highest sex ratio in Karnataka, and what was it?' },
  { emoji: '📋', label: 'Summarize Report',   prompt: 'Summarize the key findings from the Karnataka census district highlights.' },
  { emoji: '👩‍🌾', label: 'Worker Stats',       prompt: 'What is the breakdown of main workers vs marginal workers in rural Odisha?' },
]

export default function HomePage({ onSubmit, isLoading }) {
  const [inputValue, setInputValue] = useState('')

  return (
    <div className="home-page">
      {/* Logo */}
      <h1 className="home-logo">How can I help you today?</h1>

      {/* Search card */}
      <SearchBox
        onSubmit={onSubmit}
        isLoading={isLoading}
        placeholder="Ask anything about Census 2011…"
        value={inputValue}
        setValue={setInputValue}
      />

      {/* Suggestion pills */}
      <div className="suggestions">
        {SUGGESTIONS.map((s, i) => (
          <button
            key={i}
            id={`suggestion-${i}`}
            className="suggestion-pill"
            onClick={() => setInputValue(s.prompt)}
            disabled={isLoading}
          >
            <span aria-hidden="true">{s.emoji}</span>
            {s.label}
          </button>
        ))}
      </div>
    </div>
  )
}
