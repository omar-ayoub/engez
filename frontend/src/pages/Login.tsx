import { useForm } from "react-hook-form";
import { useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import { useAuthStore } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useState } from "react";
import { AlertCircle, Globe, Loader2 } from "lucide-react";

interface LoginForm {
  email: string;
  password: string;
}

export default function Login() {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const login = useAuthStore((s) => s.login);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>();

  const toggleLanguage = () => {
    i18n.changeLanguage(i18n.language === "ar" ? "en" : "ar");
  };

  const onSubmit = async (data: LoginForm) => {
    setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(data),
      });

      if (!res.ok) {
        await res.json();
        if (res.status === 423) {
          setError(t("auth.accountLocked"));
        } else {
          setError(t("auth.invalidCredentials"));
        }
        return;
      }

      const result = await res.json();
      login(result.access_token, result.user);
      navigate("/");
    } catch {
      setError(t("status.offline"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-svh flex-col items-center justify-center bg-background p-6">
      <button
        onClick={toggleLanguage}
        className="touch-target fixed top-4 end-4 z-10 inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        aria-label={t("language.toggle")}
      >
        <Globe className="size-4" />
        <span>{t("language.toggle")}</span>
      </button>

      <Card className="w-full max-w-sm border-border/50">
        <CardHeader className="text-center">
          <CardTitle className="text-4xl font-bold tracking-tight text-brand">
            {t("app.name")}
          </CardTitle>
          <CardDescription>{t("app.tagline")}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="email">{t("auth.email")}</Label>
              <Input
                id="email"
                type="email"
                dir="ltr"
                className="touch-target"
                placeholder="email@example.com"
                autoComplete="email"
                {...register("email", { required: true })}
                aria-invalid={errors.email ? "true" : undefined}
              />
              {errors.email && (
                <p className="text-xs text-destructive">
                  {t("validation.required")}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">{t("auth.password")}</Label>
              <Input
                id="password"
                type="password"
                dir="ltr"
                className="touch-target"
                autoComplete="current-password"
                {...register("password", { required: true })}
                aria-invalid={errors.password ? "true" : undefined}
              />
              {errors.password && (
                <p className="text-xs text-destructive">
                  {t("validation.required")}
                </p>
              )}
            </div>

            {error && (
              <div
                className="flex items-start gap-2 rounded-lg bg-danger/10 p-3 text-sm text-danger"
                role="alert"
              >
                <AlertCircle className="mt-0.5 size-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <Button
              type="submit"
              className="touch-target w-full bg-brand font-semibold text-white hover:bg-brand-light"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  <span>{t("common.loading")}</span>
                </>
              ) : (
                t("auth.login")
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
