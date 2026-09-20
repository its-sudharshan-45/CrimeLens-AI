import { useState } from 'react';
import {
  Compass,
  Video,
  FileSearch,
  Users,
  ShieldCheck,
  Search,
  AlertTriangle,
  RefreshCw,
  HelpCircle,
  ShieldAlert,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { PredictionDisclaimerBanner } from '@/components/ai/PredictionDisclaimerBanner';
import { useInvestigationLeads } from '@/hooks/usePredictions';

const CITIES = [
  'Delhi',
  'Mumbai',
  'Bangalore',
  'Hyderabad',
  'Kolkata',
  'Chennai',
  'Ahmedabad',
  'Pune',
  'Jaipur',
  'Lucknow',
  'Kanpur',
  'Nagpur',
  'Indore',
  'Thane',
  'Bhopal',
  'Visakhapatnam',
  'Patna',
];

const CRIME_TYPES = ['All', 'Theft', 'Burglary', 'Assault', 'Robbery', 'Cybercrime'];

export function InvestigationAssistantPanel() {
  const [city, setCity] = useState<string>('Delhi');
  const [crimeType, setCrimeType] = useState<string>('All');

  const { data, isLoading, isError, error, refetch } = useInvestigationLeads(city, crimeType);

  const getCategoryIcon = (category: string) => {
    switch (category.toLowerCase()) {
      case 'cctv review':
        return <Video size={18} className="text-blue-400" />;
      case 'historical case review':
        return <FileSearch size={18} className="text-purple-400" />;
      case 'witness & first-responder follow-up':
      case 'witness interview review':
        return <Users size={18} className="text-amber-400" />;
      case 'patrol coverage optimization':
      case 'patrol coverage review':
        return <ShieldCheck size={18} className="text-emerald-400" />;
      case 'modus operandi analysis':
      default:
        return <Search size={18} className="text-rose-400" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner: Global Ethics Disclaimer */}
      <PredictionDisclaimerBanner customText={data?.disclaimer} />

      {/* Control Header */}
      <Card className="p-4 bg-card/60 backdrop-blur border border-border">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400">
              <Compass size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-foreground">Pattern Investigation Assistant</h2>
                <Badge variant="purple">AI Advisory</Badge>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Generates pattern-based investigative priorities from historical temporal & spatial data
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* City Selector */}
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-muted-foreground">City:</span>
              <select
                value={city}
                onChange={(e) => setCity(e.target.value)}
                className="h-8 rounded-lg bg-secondary border border-border px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-purple-500"
              >
                {CITIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            {/* Crime Type Filter */}
            <div className="flex items-center gap-1.5 text-xs">
              <span className="text-muted-foreground">Crime Type:</span>
              <select
                value={crimeType}
                onChange={(e) => setCrimeType(e.target.value)}
                className="h-8 rounded-lg bg-secondary border border-border px-3 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-purple-500"
              >
                {CRIME_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              disabled={isLoading}
              className="h-8 text-xs"
            >
              <RefreshCw size={12} className={`mr-1.5 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>
      </Card>

      {/* Loading state */}
      {isLoading && (
        <div className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="p-5 animate-pulse space-y-3">
              <div className="h-4 bg-muted rounded w-1/4" />
              <div className="h-4 bg-muted rounded w-3/4" />
              <div className="h-3 bg-muted rounded w-1/2" />
            </Card>
          ))}
        </div>
      )}

      {/* Error state */}
      {isError && (
        <Card className="p-6 text-center text-red-400 space-y-2 border-red-500/30">
          <AlertTriangle size={24} className="mx-auto text-red-400" />
          <p className="text-sm font-semibold">Failed to generate investigation priorities</p>
          <p className="text-xs text-muted-foreground">{(error as Error)?.message}</p>
        </Card>
      )}

      {/* Priorities List */}
      {data && data.leads && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Ranked Investigative Priorities ({data.leads.length} Identified)
            </h3>
            <span className="text-[11px] text-muted-foreground">
              Prioritized by historical pattern correlation and operational impact
            </span>
          </div>

          <div className="space-y-3.5">
            {data.leads.map((lead) => (
              <Card
                key={lead.priority}
                className="p-5 border border-border hover:border-purple-500/40 transition-all"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-secondary border border-border flex items-center justify-center font-mono font-bold text-xs text-foreground">
                      #{lead.priority}
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded-md bg-secondary text-foreground">
                        {getCategoryIcon(lead.category)}
                      </div>
                      <h4 className="text-sm font-bold text-foreground">{lead.category}</h4>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-muted-foreground">Pattern Confidence:</span>
                    <Badge variant="purple">
                      {(lead.confidence_score * 100).toFixed(0)}% Match
                    </Badge>
                  </div>
                </div>

                {/* Recommendation Description */}
                <div className="mt-3.5">
                  <p className="text-xs text-foreground leading-relaxed font-medium">
                    {lead.description}
                  </p>
                </div>

                {/* Explicit Reason Section */}
                <div className="mt-3 p-3 rounded-lg bg-secondary/60 border border-border/80">
                  <div className="flex items-center gap-1.5 text-[11px] font-bold text-purple-300 uppercase tracking-wider mb-1">
                    <HelpCircle size={13} className="text-purple-400" />
                    Why this suggestion was generated
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {lead.reason}
                  </p>
                </div>
              </Card>
            ))}
          </div>

          {/* Ethical Guidance Footer Box */}
          <div className="p-4 rounded-xl bg-secondary/30 border border-border text-xs text-muted-foreground flex items-start gap-3">
            <ShieldAlert size={18} className="text-muted-foreground shrink-0 mt-0.5" />
            <div className="space-y-1">
              <span className="font-semibold text-foreground">
                Investigator Advisory & System Safeguards:
              </span>
              <p className="text-[11px] leading-relaxed">
                CrimeLens AI operates purely on aggregate temporal frequencies, spatio-temporal hotspot clusters, and historical modus-operandi patterns. The system strictly refuses and prevents any suspect profiling, demographic indexing, or individualized criminality scoring.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
