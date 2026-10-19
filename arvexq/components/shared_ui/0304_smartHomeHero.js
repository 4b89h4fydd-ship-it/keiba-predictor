function smartHomeHero(){
  var shared=window.ARVEXQUnifiedHome;
  if(shared)return shared.hero();
  return '<div class="arv-unified-hero"><img src="/arvexq-brush-logo.svg?v=brush-20261014" alt="ARVEXQ"></div>';
}
// Unused legacy home hub removed; unified horse home is authoritative.
