import ProductDashboard from '@/components/sections/product-dashboard';
import ProductFeatures from '@/components/sections/product-features';
import ProductHero from '@/components/sections/product-hero';
import ProductLogs from '@/components/sections/product-logs';

export default function ProductPage() {
  return (
    <>
      <ProductHero />
      <ProductDashboard />
      <ProductFeatures />
      <div className="relative">
        <div className="to-accent/50 bg-chart-1 absolute top-0 left-0 -z-3 hidden size-40 -translate-x-1/4 -translate-y-1/2 rounded-full will-change-transform lg:block" />
        <ProductLogs />
      </div>
    </>
  );
}
