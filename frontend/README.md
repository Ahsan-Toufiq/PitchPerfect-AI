# PitchPerfect AI Frontend

A modern, responsive React dashboard for the PitchPerfect AI lead generation and analysis platform.

## Features

### 🎨 Modern UI/UX
- **Dark/Light Mode**: Toggle between dark and light themes
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile
- **Professional Design**: Clean, modern interface with Tailwind CSS
- **Smooth Animations**: Fluid transitions and interactions

### 📊 Dashboard
- **Real-time Statistics**: View leads, analysis, and email metrics
- **Activity Feed**: Monitor recent system activities
- **Quick Actions**: One-click access to common tasks
- **Performance Charts**: Visual representation of data (placeholder for future implementation)

### 🔍 Lead Scraping
- **Multi-source Scraping**: Configure Yelp and Google Maps scraping
- **Advanced Configuration**: Set delays, concurrent requests, and data fields
- **Progress Tracking**: Real-time progress monitoring
- **Results Export**: Download scraped data as CSV
- **Business Categories**: Pre-defined categories for targeted scraping

### 📈 Website Analysis
- **Lighthouse Integration**: Performance, SEO, Accessibility, and Best Practices scores
- **AI-Powered Analysis**: Local LLM analysis for SEO and UX insights
- **Customizable Prompts**: Configure AI analysis parameters
- **Detailed Reports**: Issues and recommendations for each website
- **Batch Processing**: Analyze multiple websites concurrently

### 📧 Email Campaigns
- **Template Management**: Create and manage email templates
- **Variable Support**: Dynamic content with {{variables}}
- **Campaign Tracking**: Monitor send, open, and reply rates
- **SMTP Configuration**: Secure email server setup
- **Rate Limiting**: Prevent spam and maintain deliverability

### ⚙️ Settings
- **Email Configuration**: SMTP settings and authentication
- **Scraping Parameters**: Customize scraping behavior
- **Analysis Settings**: Configure Lighthouse and LLM parameters
- **Notification Preferences**: Control system alerts and notifications

## Technology Stack

- **React 18**: Modern React with hooks and functional components
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first CSS framework
- **Heroicons**: Beautiful SVG icons
- **Vite**: Fast build tool and development server

## Getting Started

### Prerequisites
- Node.js 18+ 
- npm or yarn

### Installation

1. **Clone the repository**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

4. **Open in browser**
   Navigate to `http://localhost:5173`

### Build for Production

```bash
npm run build
```

The built files will be in the `dist` directory.

## Project Structure

```
src/
├── components/          # React components
│   ├── Layout.tsx      # Main layout with sidebar and header
│   ├── Dashboard.tsx   # Dashboard with stats and activity
│   ├── LeadScraping.tsx # Lead scraping configuration
│   ├── WebsiteAnalysis.tsx # Website analysis interface
│   ├── EmailCampaigns.tsx # Email campaign management
│   └── Settings.tsx    # System settings
├── App.tsx             # Main app component
├── main.tsx           # App entry point
└── index.css          # Global styles and Tailwind
```

## Component Architecture

### Layout Component
- Responsive sidebar navigation
- Dark/light mode toggle
- Mobile-friendly hamburger menu
- Dynamic page titles

### Dashboard Component
- Statistics cards with trends
- Recent activity feed
- Quick action buttons
- Performance overview (placeholder)

### Lead Scraping Component
- Configuration form with validation
- Real-time progress tracking
- Results table with export functionality
- Tabbed interface for config/results

### Website Analysis Component
- Lighthouse score visualization
- AI analysis display
- Issues and recommendations lists
- Batch processing controls

### Email Campaigns Component
- Template management interface
- Campaign creation and tracking
- SMTP configuration
- Export functionality

### Settings Component
- Tabbed settings interface
- Form validation
- Real-time configuration updates
- Connection testing

## Styling

The application uses Tailwind CSS with:
- **Custom Components**: Reusable component classes
- **Dark Mode**: Automatic dark/light theme switching
- **Responsive Design**: Mobile-first approach
- **Consistent Spacing**: Tailwind's spacing scale
- **Color System**: Semantic color usage

## State Management

- **React Hooks**: useState for local component state
- **Props**: Component communication
- **Context**: Future implementation for global state

## Future Enhancements

### Planned Features
- **Real-time Updates**: WebSocket integration for live data
- **Advanced Charts**: D3.js or Chart.js integration
- **Data Export**: PDF reports and advanced CSV options
- **User Management**: Multi-user support with roles
- **API Integration**: Backend connectivity
- **Notifications**: Real-time system alerts
- **Analytics**: Advanced reporting and insights

### Technical Improvements
- **State Management**: Redux Toolkit or Zustand
- **Testing**: Jest and React Testing Library
- **Performance**: Code splitting and lazy loading
- **Accessibility**: ARIA labels and keyboard navigation
- **PWA**: Progressive Web App features

## Development

### Code Style
- **TypeScript**: Strict type checking
- **ESLint**: Code quality and consistency
- **Prettier**: Code formatting
- **Component Structure**: Functional components with hooks

### Best Practices
- **Component Composition**: Reusable, composable components
- **Props Interface**: TypeScript interfaces for all props
- **Error Boundaries**: Graceful error handling
- **Loading States**: Proper loading indicators
- **Responsive Design**: Mobile-first approach

## Contributing

1. Follow the existing code style
2. Add TypeScript types for all new components
3. Test on multiple screen sizes
4. Ensure dark mode compatibility
5. Update documentation for new features

## License

This project is part of the PitchPerfect AI platform.
