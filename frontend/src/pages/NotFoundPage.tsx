import { Link } from 'react-router-dom';
import { ScanEye, Home, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export default function NotFoundPage() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="text-center max-w-md animate-slide-up">
        {/* Icon */}
        <div className="w-16 h-16 rounded-2xl bg-secondary border border-border flex items-center justify-center mx-auto mb-6">
          <ScanEye size={28} className="text-muted-foreground" />
        </div>

        {/* 404 */}
        <h1 className="text-7xl font-bold text-foreground/10 mb-2">404</h1>
        <h2 className="text-xl font-semibold text-foreground mb-3">Page Not Found</h2>
        <p className="text-sm text-muted-foreground mb-8 leading-relaxed">
          The page you're looking for doesn't exist or has been moved.
          Please check the URL or navigate back to safety.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link to="/">
            <Button variant="primary" size="md" className="gap-2 w-full sm:w-auto" id="404-home-btn">
              <Home size={15} />
              Go Home
            </Button>
          </Link>
          <button
            onClick={() => window.history.back()}
            className="inline-flex items-center justify-center gap-2 h-10 px-4 text-sm font-medium text-muted-foreground hover:text-foreground border border-border rounded-lg transition-all duration-150"
            id="404-back-btn"
          >
            <ArrowLeft size={15} />
            Go Back
          </button>
        </div>
      </div>
    </div>
  );
}
