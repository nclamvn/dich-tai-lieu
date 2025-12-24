# 🎨 AI Translator Pro - Premium Dashboard

> Dashboard siêu hiện đại với Glass Morphism, Framer Motion, và Gradient Animations

## ✨ Tính năng nổi bật

### 🎭 Visual Design
- **Glass Morphism** - Hiệu ứng kính mờ cao cấp với backdrop blur
- **Gradient Backgrounds** - Gradient động với purple/blue theme
- **Animated Elements** - Mọi thành phần đều có micro-animations
- **Responsive Layout** - Tối ưu cho mọi kích thước màn hình
- **Dark Theme** - Giao diện tối hiện đại và dễ nhìn

### 🚀 Animations & Interactions
- **Framer Motion** - Smooth animations cho mọi thành phần
- **Drag & Drop** - Upload file với visual feedback
- **Progress Tracking** - Real-time progress với shimmer effect
- **Hover Effects** - Micro-interactions khi hover
- **Status Indicators** - Live badges và animated indicators

### 📊 Enhanced Features
- **Real-time Stats** - 4 stat cards với icons và animations
- **Processing Speed** - Hiển thị tốc độ xử lý real-time
- **Cost Estimation** - Tính toán chi phí dự kiến
- **File Analytics** - Thông tin chi tiết về file (size, chunks, type)
- **Enhanced Language Detection** - Support nhiều ngôn ngữ hơn

## 📦 Installation

### 1. Cài đặt Dependencies

```bash
npm install framer-motion
# hoặc
yarn add framer-motion
```

### 2. Cài đặt Tailwind CSS Plugins

```bash
npm install -D @tailwindcss/forms
# hoặc
yarn add -D @tailwindcss/forms
```

### 3. Setup Tailwind Config

Copy file `tailwind.config.js` đã được tạo sẵn vào root project của bạn.

### 4. Global CSS

Thêm vào file `globals.css` hoặc `app.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  @apply bg-slate-900/20;
}

::-webkit-scrollbar-thumb {
  @apply bg-purple-500/50 rounded-full;
}

::-webkit-scrollbar-thumb:hover {
  @apply bg-purple-500/70;
}
```

## 🎯 Usage

### Basic Usage

```tsx
import TranslatorDashboardPremium from './ui/TranslatorDashboardPremium';

function App() {
  return <TranslatorDashboardPremium />;
}
```

### Integration với Backend

Thay thế phần `onTranslate()` function để kết nối với API backend:

```tsx
async function onTranslate() {
  if (!readyToTranslate()) {
    setError("Please enter a valid API key and select a file.");
    return;
  }

  setError("");
  setStatus("translating");
  setProgress(0);

  try {
    // Tạo job trên backend
    const response = await fetch('http://localhost:8000/api/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_name: file?.name || 'Translation Job',
        input_file: file?.path,
        output_file: `output/${file?.name}`,
        source_lang: detectedLanguage,
        target_lang: 'vi',
        priority: 10,
        provider: 'openai',
        model: model,
      })
    });

    const job = await response.json();

    // Poll progress
    const interval = setInterval(async () => {
      const statusRes = await fetch(`http://localhost:8000/api/jobs/${job.job_id}`);
      const jobStatus = await statusRes.json();

      setProgress(jobStatus.progress * 100);

      if (jobStatus.status === 'completed') {
        clearInterval(interval);
        setStatus('done');
      } else if (jobStatus.status === 'failed') {
        clearInterval(interval);
        setStatus('error');
        setError(jobStatus.error_message);
      }
    }, 1000);

  } catch (error) {
    setStatus('error');
    setError(error.message);
  }
}
```

## 🎨 Component Structure

### Main Components

```
TranslatorDashboardPremium/
├── GlassCard           - Reusable glass morphism card
├── StatCard            - Animated stat display card
├── StatusBadge         - Live status indicator
└── LiveIndicator       - Animated "LIVE" badge
```

### Layout Grid

```
┌─────────────────────────────────────────────┐
│  Header (Logo + Status)                     │
├───────────┬─────────────────────────────────┤
│   Left    │         Right Column            │
│  Column   │                                 │
│           │  ┌─────────────────────────┐    │
│ API Key   │  │   Stats Grid (4 cards)  │    │
│ Model     │  └─────────────────────────┘    │
│           │                                 │
│ Upload    │  ┌─────────────────────────┐    │
│ File      │  │   Progress Card         │    │
│           │  └─────────────────────────┘    │
│ Translate │                                 │
│ Button    │  ┌─────────────────────────┐    │
│           │  │   Download Actions      │    │
└───────────┴──└─────────────────────────┘────┘
```

## 🎭 Design System

### Color Palette

```javascript
Primary:   Purple (#A855F7)
Secondary: Blue (#3B82F6)
Background: Slate (#0F172A - #1E293B)
Glass: White with 5-10% opacity
Border: Purple/400 with 20% opacity
```

### Typography

- **Headers**: Gradient text (white → purple-200)
- **Body**: White / Purple-200
- **Captions**: Purple-200 with 60% opacity
- **Mono**: Font-mono for numbers/codes

### Spacing & Sizing

- **Cards**: rounded-2xl to rounded-3xl
- **Padding**: 4-6 (16-24px)
- **Gap**: 3-6 (12-24px)
- **Border**: 1px with low opacity

## ⚡ Performance Tips

1. **Lazy Load Framer Motion**: Chỉ import khi cần thiết
2. **Optimize Images**: Sử dụng Next.js Image nếu có
3. **Reduce Animations**: Giảm animations trên mobile
4. **Virtualize Lists**: Nếu có nhiều items trong list

## 🔧 Customization

### Thay đổi Color Scheme

Trong `tailwind.config.js`:

```javascript
theme: {
  extend: {
    colors: {
      primary: '#YOUR_COLOR',
      secondary: '#YOUR_COLOR',
    }
  }
}
```

### Thay đổi Animation Speed

Trong component:

```tsx
<motion.div
  transition={{ duration: 0.5 }} // Thay đổi tại đây
>
```

### Custom Glassmorphism

```tsx
className="bg-white/10 backdrop-blur-xl border border-white/20"
```

## 📱 Responsive Breakpoints

- **Mobile**: < 640px (sm)
- **Tablet**: 640px - 1024px (md, lg)
- **Desktop**: > 1024px (lg, xl, 2xl)

## 🐛 Troubleshooting

### Framer Motion không hoạt động

```bash
# Reinstall framer-motion
npm install framer-motion@latest
```

### Backdrop blur không hoạt động

Thêm vào `tailwind.config.js`:

```javascript
variants: {
  extend: {
    backdropBlur: ['responsive']
  }
}
```

### Animations bị giật

```tsx
// Thêm will-change
className="will-change-transform"
```

## 📚 Resources

- [Framer Motion Docs](https://www.framer.com/motion/)
- [Tailwind CSS Docs](https://tailwindcss.com/docs)
- [Glass Morphism Generator](https://hype4.academy/tools/glassmorphism-generator)
- [Gradient Generator](https://cssgradient.io/)

## 🎓 Advanced Features (Coming Soon)

- [ ] Real-time collaboration
- [ ] Charts & analytics (Chart.js / Recharts)
- [ ] Dark/Light mode toggle
- [ ] Custom themes
- [ ] Export settings
- [ ] Keyboard shortcuts
- [ ] Mobile gestures

## 📄 License

MIT License - Use freely in your projects!

---

**Created by**: AI Translator Pro Team
**Version**: 1.0.0 (Premium)
**Last Updated**: 2024

💜 **Enjoy your new premium dashboard!**
