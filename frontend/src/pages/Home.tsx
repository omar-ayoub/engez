import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router";
import { useAuthStore } from "@/lib/auth";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import { Button } from "@/components/ui/button";
import {
  Globe,
  Home as HomeIcon,
  LogOut,
  Plus,
  Receipt,
  Settings,
  Wifi,
  WifiOff,
} from "lucide-react";

export default function Home() {
  const { t, i18n } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();
  const { isOnline } = useOnlineStatus();

  if (!user) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-background">
        <div className="size-6 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  const displayName = i18n.language === "ar" ? user.name_ar : user.name;
  const companyName =
    i18n.language === "ar" ? user.company_name_ar : user.company_name;

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="flex min-h-svh flex-col bg-background text-foreground">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-base font-semibold">
            {t("home.welcome", { name: displayName })}
          </h1>
          <p className="truncate text-xs text-muted-foreground">
            {companyName}
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          <StatusIndicator
            isOnline={isOnline}
            label={isOnline ? t("status.online") : t("status.offline")}
          />
          <button
            onClick={() =>
              i18n.changeLanguage(i18n.language === "ar" ? "en" : "ar")
            }
            className="touch-target inline-flex items-center justify-center rounded-lg p-2 text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label={t("language.toggle")}
          >
            <Globe className="size-4" />
          </button>
          <button
            onClick={handleLogout}
            className="touch-target inline-flex items-center justify-center rounded-lg p-2 text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label={t("auth.logout")}
          >
            <LogOut className="size-4" />
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="flex flex-1 flex-col items-center justify-center p-6">
        <Button
          onClick={() => navigate("/capture")}
          className="touch-target h-14 gap-2 rounded-2xl bg-brand px-8 text-lg font-semibold text-white hover:bg-brand-light active:scale-[0.97] transition-[colors,transform]"
        >
          <Plus className="size-5" />
          {t("expense.new")}
        </Button>
      </main>

      {/* Bottom navigation */}
      <nav
        className="flex items-center justify-around border-t border-border px-2 py-1"
        style={{ paddingBottom: "max(0.25rem, env(safe-area-inset-bottom))" }}
      >
        <NavItem icon={HomeIcon} label={t("nav.home")} active onPress={() => navigate("/")} />
        <NavItem icon={Receipt} label={t("nav.expenses")} onPress={() => navigate("/drafts")} />
        <NavItem icon={Settings} label={t("nav.settings")} onPress={() => navigate("/settings/integrations")} />
      </nav>
    </div>
  );
}

function StatusIndicator({
  isOnline,
  label,
}: {
  isOnline: boolean;
  label: string;
}) {
  return (
    <div
      className="flex items-center gap-1.5 rounded-full bg-secondary px-2.5 py-1 text-xs text-muted-foreground"
      role="status"
      aria-label={label}
    >
      {isOnline ? (
        <Wifi className="size-3 text-success" />
      ) : (
        <WifiOff className="size-3 text-danger" />
      )}
      <span>{label}</span>
    </div>
  );
}

function NavItem({
  icon: Icon,
  label,
  active = false,
  onPress,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  active?: boolean;
  onPress?: () => void;
}) {
  return (
    <button
      onClick={onPress}
      aria-current={active ? "page" : undefined}
      className={`touch-target flex flex-col items-center justify-center gap-0.5 rounded-lg px-4 py-2 text-xs transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
        active
          ? "font-medium text-brand"
          : "text-muted-foreground hover:text-foreground"
      }`}
    >
      <Icon className="size-5" />
      <span>{label}</span>
    </button>
  );
}
