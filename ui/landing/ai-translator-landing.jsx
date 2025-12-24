/**
 * AI Translator Pro Landing Page
 * Design: Notion + Apple Minimalist (Bold & Quiet)
 * Colors: Black & White only
 *
 * Dependencies:
 * - React 18+
 * - Tailwind CSS
 * - Lucide React icons
 * - framer-motion (optional, for animations)
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Languages,
  Code2,
  Layout,
  Zap,
  Check,
  ArrowRight,
  FileText,
  Sparkles,
  ChevronDown
} from 'lucide-react';

// ============================================================================
// ANIMATION HOOKS
// ============================================================================

const useScrollReveal = (threshold = 0.1) => {
  const ref = useRef(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.unobserve(entry.target);
        }
      },
      { threshold }
    );

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => observer.disconnect();
  }, [threshold]);

  return [ref, isVisible];
};

const useCountUp = (end, duration = 2000, start = 0) => {
  const [count, setCount] = useState(start);
  const [isActive, setIsActive] = useState(false);

  useEffect(() => {
    if (!isActive) return;

    let startTime = null;
    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      setCount(Math.floor(progress * (end - start) + start));
      if (progress < 1) {
        requestAnimationFrame(animate);
      }
    };
    requestAnimationFrame(animate);
  }, [isActive, end, duration, start]);

  return [count, setIsActive];
};

// ============================================================================
// COMPONENTS
// ============================================================================

// Navigation
const Navigation = () => {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <nav className={`fixed top-0 left-0 right-0 z-50 h-20 transition-all duration-300 ${
      scrolled ? 'bg-white/80 backdrop-blur-md border-b border-gray-200' : 'bg-transparent'
    }`}>
      <div className="max-w-[1200px] mx-auto px-6 h-full flex items-center justify-between">
        <span className="text-xl font-medium tracking-tight">AI Translator</span>
        <button className="px-6 py-2.5 border border-black text-sm uppercase tracking-wider font-medium
                         hover:bg-black hover:text-white transition-all duration-200">
          Đăng Nhập
        </button>
      </div>
    </nav>
  );
};

// Hero Section
const Hero = () => {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setLoaded(true);
  }, []);

  return (
    <section className="min-h-screen flex flex-col items-center justify-center px-6 relative">
      <div className="text-center">
        {/* Title Line 1 */}
        <h1
          className={`text-[56px] md:text-[120px] font-semibold uppercase tracking-[-0.03em] leading-[0.9]
                     transition-all duration-700 ease-out ${
                       loaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
                     }`}
          style={{ transitionDelay: '100ms' }}
        >
          Dịch Tài Liệu
        </h1>

        {/* Title Line 2 */}
        <h1
          className={`text-[56px] md:text-[120px] font-semibold uppercase tracking-[-0.03em] leading-[0.9]
                     transition-all duration-700 ease-out ${
                       loaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
                     }`}
          style={{ transitionDelay: '200ms' }}
        >
          Chuyên Nghiệp
        </h1>

        {/* Subtitle */}
        <p
          className={`text-lg text-gray-500 mt-10 transition-all duration-700 ease-out ${
            loaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
          }`}
          style={{ transitionDelay: '300ms' }}
        >
          Bảo toàn công thức. Giữ nguyên code. Định dạng hoàn hảo.
        </p>

        {/* CTA Button */}
        <button
          className={`mt-12 px-10 py-5 border border-black text-base uppercase tracking-wider font-medium
                     inline-flex items-center gap-3 group
                     hover:bg-black hover:text-white transition-all duration-200 ${
                       loaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
                     }`}
          style={{ transitionDelay: '400ms' }}
        >
          Bắt Đầu Miễn Phí
          <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
        </button>
      </div>

      {/* Scroll Indicator */}
      <div
        className={`absolute bottom-12 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2
                   transition-all duration-700 ${loaded ? 'opacity-100' : 'opacity-0'}`}
        style={{ transitionDelay: '600ms' }}
      >
        <span className="text-xs text-gray-400 uppercase tracking-widest">Scroll</span>
        <ChevronDown className="w-5 h-5 text-gray-400 animate-bounce" />
      </div>
    </section>
  );
};

// Product Demo Section
const ProductDemo = () => {
  const [ref, isVisible] = useScrollReveal();

  const sourceCode = `def calculate_energy(mass):
    """Calculate E = mc^2"""
    c = 299792458  # m/s
    return mass * c ** 2

# Formula: $E = mc^2$
# Integral: $$\\int_0^\\infty e^{-x^2} dx$$`;

  const outputCode = `def tính_năng_lượng(khối_lượng):
    """Tính E = mc²"""
    c = 299792458  # m/s
    return khối_lượng * c ** 2

# Công thức: $E = mc^2$
# Tích phân: $$\\int_0^\\infty e^{-x^2} dx$$`;

  return (
    <section
      ref={ref}
      className={`py-20 md:py-40 px-6 transition-all duration-800 ease-out ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
      }`}
    >
      <div className="max-w-[1200px] mx-auto border border-gray-200 p-8 md:p-20">
        <div className="grid md:grid-cols-2 gap-8 md:gap-16">
          {/* Source */}
          <div>
            <span className="text-xs text-gray-500 uppercase tracking-widest flex items-center gap-2">
              <FileText className="w-4 h-4" strokeWidth={1.5} />
              Source
            </span>
            <pre className="mt-4 p-6 bg-gray-50 font-mono text-sm leading-relaxed overflow-x-auto">
              {sourceCode}
            </pre>
          </div>

          {/* Output */}
          <div>
            <span className="text-xs text-gray-500 uppercase tracking-widest flex items-center gap-2">
              <Sparkles className="w-4 h-4" strokeWidth={1.5} />
              Output
            </span>
            <pre className="mt-4 p-6 bg-gray-50 font-mono text-sm leading-relaxed overflow-x-auto">
              {outputCode}
            </pre>
            <p className="mt-4 text-sm text-gray-500 flex items-center gap-2">
              <Check className="w-4 h-4" strokeWidth={1.5} />
              Formula preserved
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};

// Metrics Section
const MetricItem = ({ value, label, suffix = '' }) => {
  const [ref, isVisible] = useScrollReveal();
  const numericValue = parseInt(value.replace(/\D/g, ''));
  const [count, setIsActive] = useCountUp(numericValue);

  useEffect(() => {
    if (isVisible) setIsActive(true);
  }, [isVisible, setIsActive]);

  return (
    <div ref={ref} className="text-center py-8">
      <div className="text-5xl md:text-7xl font-semibold tracking-tight">
        {count}{suffix}
      </div>
      <div className="text-sm text-gray-500 uppercase tracking-widest mt-2">
        {label}
      </div>
    </div>
  );
};

const Metrics = () => {
  const [ref, isVisible] = useScrollReveal();

  return (
    <section
      ref={ref}
      className={`py-20 md:py-32 px-6 transition-all duration-800 ease-out ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
      }`}
    >
      <div className="max-w-[1000px] mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-gray-200">
          <MetricItem value="94" label="Accuracy" suffix="%" />
          <MetricItem value="204" label="Tests" suffix="+" />
          <MetricItem value="100" label="Pages/min" suffix="+" />
        </div>
      </div>
    </section>
  );
};

// Features Section
const FeatureCard = ({ icon: Icon, title, description }) => {
  return (
    <div className="p-8 md:p-16 bg-white hover:bg-gray-50 transition-colors duration-200 group">
      <Icon className="w-6 h-6" strokeWidth={1.5} />
      <h3 className="text-2xl font-medium mt-6">{title}</h3>
      <p className="text-gray-500 mt-3 leading-relaxed">{description}</p>
    </div>
  );
};

const Features = () => {
  const [ref, isVisible] = useScrollReveal();

  const features = [
    {
      icon: Languages,
      title: 'Dịch Thông Minh',
      description: 'GPT-4 & Claude với ngữ cảnh chuyên ngành'
    },
    {
      icon: Code2,
      title: 'Bảo Toàn STEM',
      description: 'Công thức LaTeX, code blocks nguyên vẹn'
    },
    {
      icon: Layout,
      title: 'Định Dạng Chuyên Nghiệp',
      description: 'Book · Report · Legal · Academic'
    },
    {
      icon: Zap,
      title: 'Xử Lý Hàng Loạt',
      description: 'Từ 1 đến hàng trăm trang'
    }
  ];

  return (
    <section
      ref={ref}
      className={`py-20 md:py-40 px-6 transition-all duration-800 ease-out ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
      }`}
    >
      <div className="max-w-[1200px] mx-auto">
        <h2 className="text-4xl md:text-5xl font-medium uppercase tracking-tight text-center mb-16">
          Tính Năng
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 border border-gray-200">
          {features.map((feature, index) => (
            <div
              key={index}
              className={`${index < 2 ? 'border-b border-gray-200' : ''}
                         ${index % 2 === 0 ? 'md:border-r border-gray-200' : ''}`}
            >
              <FeatureCard {...feature} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

// How It Works Section
const StepItem = ({ number, title, description }) => {
  return (
    <div className="text-center md:text-left">
      <div className="text-[80px] md:text-[120px] font-extralight text-gray-200 leading-none">
        {number}
      </div>
      <h3 className="text-2xl font-medium mt-2 uppercase tracking-wide">{title}</h3>
      <p className="text-gray-500 mt-2">{description}</p>
    </div>
  );
};

const HowItWorks = () => {
  const [ref, isVisible] = useScrollReveal();

  const steps = [
    { number: '01', title: 'Tải Lên', description: 'Kéo thả file PDF, DOCX' },
    { number: '02', title: 'Chọn', description: 'Ngôn ngữ & template' },
    { number: '03', title: 'Nhận', description: 'DOCX hoàn chỉnh' }
  ];

  return (
    <section
      ref={ref}
      className={`py-20 md:py-40 px-6 bg-white transition-all duration-800 ease-out ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
      }`}
    >
      <div className="max-w-[1200px] mx-auto">
        <h2 className="text-4xl md:text-5xl font-medium uppercase tracking-tight text-center mb-20">
          Cách Hoạt Động
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-12 md:gap-8">
          {steps.map((step, index) => (
            <React.Fragment key={index}>
              <StepItem {...step} />
              {index < steps.length - 1 && (
                <div className="hidden md:flex items-center justify-center text-gray-200 text-2xl absolute">
                  {/* Arrow would go here but it's tricky with grid */}
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>
    </section>
  );
};

// Trust Section
const Trust = () => {
  const [ref, isVisible] = useScrollReveal();

  const trustItems = [
    '204+ automated tests',
    'E2E pipeline verified',
    'STEM content preserved',
    '4 professional templates',
    'Production-grade code',
    'Enterprise ready'
  ];

  return (
    <section
      ref={ref}
      className={`py-20 md:py-40 px-6 transition-all duration-800 ease-out ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
      }`}
    >
      <div className="max-w-[600px] mx-auto md:mx-0 md:ml-[calc((100%-1200px)/2+24px)]">
        <h2 className="text-4xl md:text-5xl font-medium uppercase tracking-tight mb-12">
          Đã Kiểm Chứng
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {trustItems.map((item, index) => (
            <div key={index} className="flex items-center gap-3">
              <Check className="w-4 h-4 flex-shrink-0" strokeWidth={1.5} />
              <span className="text-base">{item}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

// Final CTA Section
const FinalCTA = () => {
  const [ref, isVisible] = useScrollReveal();

  return (
    <section
      ref={ref}
      className={`py-32 md:py-52 px-6 text-center transition-all duration-800 ease-out ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
      }`}
    >
      <h2 className="text-5xl md:text-7xl font-semibold uppercase tracking-tight">
        Sẵn Sàng?
      </h2>

      <button className="mt-12 px-12 py-6 bg-black text-white text-base uppercase tracking-wider font-medium
                       inline-flex items-center gap-3 group
                       hover:bg-gray-800 transition-all duration-200">
        Bắt Đầu Ngay
        <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
      </button>
    </section>
  );
};

// Footer
const Footer = () => {
  return (
    <footer className="h-20 border-t border-gray-200 px-6">
      <div className="max-w-[1200px] mx-auto h-full flex items-center justify-between">
        <span className="text-sm text-gray-500">
          AI Translator Pro v2.0
        </span>
        <div className="text-sm text-gray-500 space-x-6">
          <a href="#" className="hover:text-black transition-colors">Điều khoản</a>
          <span>·</span>
          <a href="#" className="hover:text-black transition-colors">Bảo mật</a>
          <span>·</span>
          <a href="#" className="hover:text-black transition-colors">Liên hệ</a>
        </div>
      </div>
    </footer>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const AITranslatorLanding = () => {
  return (
    <div className="min-h-screen bg-white text-black font-sans antialiased">
      <style jsx global>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@200;400;500;600&display=swap');

        :root {
          --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }

        body {
          font-family: var(--font-sans);
        }

        /* Smooth scroll */
        html {
          scroll-behavior: smooth;
        }

        /* Custom scrollbar */
        ::-webkit-scrollbar {
          width: 8px;
        }

        ::-webkit-scrollbar-track {
          background: transparent;
        }

        ::-webkit-scrollbar-thumb {
          background: #E5E5E5;
          border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
          background: #CCCCCC;
        }
      `}</style>

      <Navigation />
      <Hero />
      <ProductDemo />
      <Metrics />
      <Features />
      <HowItWorks />
      <Trust />
      <FinalCTA />
      <Footer />
    </div>
  );
};

export default AITranslatorLanding;
