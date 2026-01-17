# GaaS Gateway Dashboard

A modern, professional dashboard for managing Gateway-as-a-Service built with Next.js 14, TypeScript, Tailwind CSS, and shadcn/ui.

## Quick Start

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm run dev
   ```

3. **Open** [http://localhost:3000](http://localhost:3000)

**Note:** Make sure the FastAPI backend is running on `http://127.0.0.1:8000` before using the dashboard.

## Configuration

The API base URL can be configured via environment variable. Create `.env.local` in the frontend directory:

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

## Features

- 🎨 **Dark Mode by Default** - Professional dark theme optimized for developer workflows
- 📱 **Responsive Design** - Clean, modern layout inspired by Cloudflare and Vercel dashboards
- 🧩 **shadcn/ui Components** - High-quality, accessible UI components
- ⚡ **Next.js 14 App Router** - Latest Next.js features with App Router
- 🔷 **TypeScript** - Full type safety throughout the application

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui
- **Icons**: Lucide React

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

1. Install dependencies:
```bash
npm install
```

2. Run the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout with dark mode
│   ├── page.tsx             # Dashboard home page
│   └── globals.css          # Global styles and theme
├── components/
│   ├── dashboard/
│   │   ├── dashboard-layout.tsx  # Main dashboard layout
│   │   ├── sidebar.tsx           # Navigation sidebar
│   │   └── header.tsx            # Top header bar
│   └── ui/                  # shadcn/ui components
└── lib/
    └── utils.ts             # Utility functions
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## Components

### Dashboard Layout

The dashboard uses a professional sidebar + header layout:

- **Sidebar**: Navigation menu with icons
- **Header**: Search bar, notifications, and user menu
- **Main Content**: Scrollable content area

### Pages

- `/` - Dashboard overview with stats and quick actions
- `/services` - Service management (to be implemented)
- `/analytics` - Analytics and usage statistics (to be implemented)
- `/activity` - Activity log (to be implemented)
- `/settings` - Settings page (to be implemented)

## Customization

### Theme

The theme is configured in `app/globals.css` using CSS variables. Dark mode is enabled by default in `app/layout.tsx`.

### Adding Components

Use shadcn/ui CLI to add new components:

```bash
npx shadcn@latest add [component-name]
```

## License

[Specify your license here]
