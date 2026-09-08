// Optional C++17 accelerator. Policies see PublicView only; all ranks behind
// the hole and all future cards stay in the game engine. No fast-math required.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>
using Clock = std::chrono::steady_clock;
constexpr int STATES = 1320, METHODS = 7, BETS = 3, MODES = METHODS * BETS;
using Features = std::array<double, 10>;
struct PublicView { std::array<int, 10> counts{}; int visible = 0; int dealt = 0; };
int index_of(int up, int raw, bool ace, int kind) { return (((up-1)*22+raw)*2+ace)*3+kind; }
int total(int raw, bool ace) { return ace && raw <= 11 ? raw+10 : raw; }
const int hilo_tags[10] = {-1,1,1,1,1,1,0,0,0,-1};
struct Linear {
    std::string name; unsigned dimensions;
    std::vector<Features> features;
    double edge;
    std::vector<double> edge_coeff, coefficients;
};
struct Models {
    std::array<unsigned char, STATES> baseline;
    std::array<std::array<double,4>,STATES> base;
    std::array<std::array<unsigned char,STATES>,97> hilo;
    std::array<double,97> baseline_edges, hilo_edges;
    std::array<Linear,METHODS-2> linear;
    template<typename T> static void read(std::ifstream &s, T &v) {
        s.read(reinterpret_cast<char*>(&v), sizeof(v));
        if (!s) throw std::runtime_error("Truncated model file");
    }
    explicit Models(const std::string &path) {
        uint16_t endian = 1;
        if (*reinterpret_cast<char*>(&endian)!=1) throw std::runtime_error("Requires little-endian host");
        std::ifstream s(path,std::ios::binary); char magic[8]{}; s.read(magic,8);
        if (!s) throw std::runtime_error("Cannot read model header");
        if (std::string(magic,8)!="BJCOUNT1") throw std::runtime_error("Wrong model file");
        uint32_t states, methods; read(s,states); read(s,methods);
        if (states!=STATES || methods!=METHODS) throw std::runtime_error("Wrong model dimensions");
        read(s,baseline); read(s,base); read(s,hilo); read(s,baseline_edges); read(s,hilo_edges);
        for (auto &m:linear) {
            uint32_t n; read(s,n);
            if (n>100) throw std::runtime_error("Invalid method name");
            m.name.resize(n); s.read(m.name.data(),n); read(s,m.dimensions);
            if (m.dimensions>10 || !m.dimensions) throw std::runtime_error("Invalid feature dimensions");
            m.features.resize(m.dimensions); for (auto &r:m.features) read(s,r);
            read(s,m.edge); m.edge_coeff.resize(m.dimensions);
            for (auto &x:m.edge_coeff) read(s,x);
            m.coefficients.resize(STATES*4*m.dimensions);
            for (auto &x:m.coefficients) read(s,x);
        }
    }
    std::string name(int m) const { return m==0?"baseline":m==1?"hilo":linear[m-2].name; }
    int hilo_index(const PublicView &v) const {
        int rc=0; for (int c=0;c<10;c++) rc+=v.counts[c]*hilo_tags[c];
        // nearbyint uses round-to-nearest/ties-to-even, matching Python round.
        return std::clamp(int(std::nearbyint(208.0*rc/(312-v.visible))),-48,48)+48;
    }
    Features get_features(int method,const PublicView &v) const {
        Features out{}; const auto &m=linear[method-2];
        for (unsigned j=0;j<m.dimensions;j++) {
            for (int c=0;c<10;c++) out[j]+=m.features[j][c]*v.counts[c];
            out[j]/=312-v.visible;
        }
        return out;
    }
    double estimate(int method,const PublicView &v) const {
        if (method<2) return method==0?baseline_edges[hilo_index(v)]:hilo_edges[hilo_index(v)];
        const auto &m=linear[method-2]; auto f=get_features(method,v); double e=m.edge;
        for (unsigned j=0;j<m.dimensions;j++) e+=m.edge_coeff[j]*f[j];
        return e;
    }
    int choose(int method,int up,int raw,bool ace,int kind,const PublicView &v) const {
        int i=index_of(up,raw,ace,kind);
        if (method==0) return baseline[i];
        if (method==1) return hilo[hilo_index(v)][i];
        const auto &m=linear[method-2]; auto f=get_features(method,v);
        int best=0; double best_value=-1e100;
        for (int a=0;a<4;a++) {
            double x=base[i][a];
            for (unsigned j=0;j<m.dimensions;j++) x+=m.coefficients[(i*4+a)*m.dimensions+j]*f[j];
            if (x>best_value) {best_value=x;best=a;}
        }
        return best;
    }
};
struct HandEnd { int value, wager; };
struct Round { double unit, edge; int cards, visible; std::array<double,BETS> bets; };
class Game {
    const std::vector<int> &cards;
    const Models &models;
    int method, pos=0;
    PublicView view;
    void observe(int c) {view.counts[c-1]++;view.visible++;}
    int draw(bool visible=true) {
        if (pos==int(cards.size())) throw std::runtime_error("Shoe exhausted inside round");
        int c=cards[pos++]; view.dealt++;
        if (visible) observe(c);
        return c;
    }
    void hand(int c,int d,int origin,int up,std::vector<HandEnd> &ends) {
        int raw=c+d, length=2; bool ace=c==1 || d==1;
        if (origin==2) {ends.push_back({total(raw,ace),1});return;}
        while (raw<=21) {
            int kind=length>2?0:origin==0 && c==d?2:1;
            int action=models.choose(method,up,raw,ace,kind,view);
            if (action==0) {ends.push_back({total(raw,ace),1});return;}
            if (action==3) {
                if (origin!=0 || length!=2 || c!=d) throw std::runtime_error("Illegal split");
                int child_origin=c==1?2:1;
                hand(c,draw(),child_origin,up,ends);
                hand(c,draw(),child_origin,up,ends);
                return;
            }
            if ((action!=1 && action!=2) || (action==2 && length!=2)) throw std::runtime_error("Illegal action");
            int next=draw();raw+=next;ace=ace||next==1;length++;
            if (action==2) {ends.push_back({total(raw,ace),2});return;}
        }
        ends.push_back({raw,1});
    }
public:
    Game(const std::vector<int> &cards,const Models &models,int method):cards(cards),models(models),method(method) {}
    int dealt() const {return pos;}
    Round round(double minimum,double maximum,double ramp) {
        // All betting alternatives are fixed before the first card is dealt.
        double edge=models.estimate(method,view);
        std::array<double,BETS> bets = {minimum,minimum+(maximum-minimum)*std::clamp(edge/ramp,0.0,1.0),edge>0?maximum:minimum};
        int old_pos=pos,old_visible=view.visible;
        int c=draw(),up=draw(),d=draw(),hole=draw(false);
        bool natural=(c==1 && d==10)||(c==10 && d==1);
        double payoff;
        if ((up==1 && hole==10)||(up==10 && hole==1)) {observe(hole);payoff=natural?0:-1;}
        else if (natural) payoff=1.5;
        else {
            std::vector<HandEnd> ends; ends.reserve(2);hand(c,d,0,up,ends);
            bool live=false;for (auto h:ends) if (h.value<=21) live=true;
            int dealer=0;
            if (live) {
                observe(hole); int raw=up+hole;bool ace=up==1||hole==1;
                while (total(raw,ace)<17) {int c=draw();raw+=c;ace=ace||c==1;}
                dealer=total(raw,ace);
            }
            payoff=0;
            for (auto h:ends) payoff+=h.value>21?-h.wager:dealer>21||h.value>dealer?h.wager:h.value<dealer?-h.wager:0;
        }
        return {payoff,edge,pos-old_pos,view.visible-old_visible,bets};
    }
};
struct Cycle {
    double x=0,w=0,q=0,predicted=0,unit=0,min_bet=1e100,max_bet=0;
    int n=0,cards=0,visible=0,raised=0;
    void add(const Round &r,int bet,double minimum) {
        double b=r.bets[bet],profit=b*r.unit;
        x+=profit;w+=b;q+=profit*profit;predicted+=r.edge;unit+=r.unit;n++;
        cards+=r.cards;visible+=r.visible;raised+=b>minimum;
        min_bet=std::min(min_bet,b);max_bet=std::max(max_bet,b);
    }
    std::array<double,3> triple() const {return {x,double(n),w};}
};
struct Stats {
    uint64_t k=0,n=0,cards=0,visible=0,raised=0;int max_cards=0;
    double x=0,w=0,q=0,xx=0,nn=0,ww=0,xn=0,xw=0,predicted=0,unit=0,res=0,rr=0,rn=0,min_bet=1e100,max_bet=0;
    void add(const Cycle &c) {
        k++;n+=c.n;x+=c.x;w+=c.w;q+=c.q;xx+=c.x*c.x;nn+=double(c.n)*c.n;ww+=c.w*c.w;
        xn+=c.x*c.n;xw+=c.x*c.w;predicted+=c.predicted;unit+=c.unit;
        double r=c.unit-c.predicted;res+=r;rr+=r*r;rn+=r*c.n;
        cards+=c.cards;visible+=c.visible;raised+=c.raised;max_cards=std::max(max_cards,c.cards);
        min_bet=std::min(min_bet,c.min_bet);max_bet=std::max(max_bet,c.max_bet);
    }
    void print() const {
        std::cout<<"["<<k<<","<<n<<","<<x<<","<<w<<","<<q<<","<<xx<<","<<nn<<","<<ww<<","<<xn<<","<<xw<<","<<predicted<<","<<unit
                 <<","<<res<<","<<rr<<","<<rn<<","<<cards<<","<<visible<<","<<raised<<","<<min_bet<<","<<max_bet<<","<<max_cards<<"]";
    }
};
struct Pair {
    int a,b; std::array<double,9> cross{};
    void add(const std::array<Cycle,MODES> &c) {
        auto x=c[a].triple(),y=c[b].triple();
        for (int i=0;i<3;i++) for (int j=0;j<3;j++) cross[i*3+j]+=x[i]*y[j];
    }
};
uint64_t uniform(std::mt19937_64 &rng,uint64_t n) {
    uint64_t threshold=uint64_t(-n)%n,x;
    do {x=rng();} while (x<threshold);
    return x%n;
}
std::vector<int> shuffle(std::mt19937_64 &rng) {
    std::vector<int> deck;deck.reserve(312);
    for (int c=1;c<=10;c++) for (int j=0;j<(c==10?96:24);j++) deck.push_back(c);
    for (int i=311;i>0;i--) std::swap(deck[i],deck[uniform(rng,i+1)]);
    return deck;
}
int main(int argc,char **argv) {
    try {
        if (argc<5) throw std::runtime_error("Usage: binary models shoes seed threshold [min max ramp] OR binary models trace decks-file threshold");
        Models models(argv[1]);int threshold=std::stoi(argv[4]);
        if (std::string(argv[2])=="trace") {
            std::ifstream in(argv[3]);int count;in>>count;
            std::cout<<std::setprecision(17);
            for (int shoe=0;shoe<count;shoe++) {
                int size;in>>size;std::vector<int> cards(size);for (int &c:cards) in>>c;
                if (!in) throw std::runtime_error("Invalid trace cards");
                for (int m=0;m<METHODS;m++) {
                    Game game(cards,models,m);int round=0;
                    do {auto r=game.round(1,4,.01);
                        std::cout<<shoe<<" "<<m<<" "<<round++<<" "<<r.unit<<" "<<r.edge<<" "<<r.cards<<" "<<r.visible;
                        for (double b:r.bets) std::cout<<" "<<b;
                        std::cout<<"\n";
                    } while (game.dealt()<threshold);
                }
            }
            return 0;
        }
        if (threshold!=26 && threshold!=52 && threshold!=104 && threshold!=156)
            throw std::runtime_error("Threshold must be 26, 52, 104, or 156");
        uint64_t shoes=std::stoull(argv[2]),seed=std::stoull(argv[3]);
        double minimum=argc>5?std::stod(argv[5]):1,maximum=argc>6?std::stod(argv[6]):4,ramp=argc>7?std::stod(argv[7]):.01;
        if (shoes<2 || !std::isfinite(minimum)||!std::isfinite(maximum)||!std::isfinite(ramp)||minimum<=0||maximum<minimum||ramp<=0)
            throw std::runtime_error("Invalid evaluation configuration");
        std::mt19937_64 rng(seed);std::array<Stats,MODES> stats;std::array<double,METHODS> seconds{};
        std::vector<Pair> pairs;
        for (int mode=1;mode<MODES;mode++) pairs.push_back({0,mode,{}});
        for (int m=2;m<METHODS;m++) for (int b=0;b<BETS;b++) pairs.push_back({BETS+b,m*BETS+b,{}});
        for (int m=0;m<METHODS;m++) for (int b=1;b<BETS;b++) if (m!=0) pairs.push_back({m*BETS,m*BETS+b,{}});
        auto start=Clock::now();
        for (uint64_t shoe=0;shoe<shoes;shoe++) {
            auto deck=shuffle(rng);std::array<Cycle,MODES> cycles;
            for (int m=0;m<METHODS;m++) {
                auto begin=Clock::now();Game game(deck,models,m);
                do {auto r=game.round(minimum,maximum,ramp);for (int b=0;b<BETS;b++) cycles[m*BETS+b].add(r,b,minimum);}
                while (game.dealt()<threshold);
                seconds[m]+=std::chrono::duration<double>(Clock::now()-begin).count();
                for (int b=0;b<BETS;b++) stats[m*BETS+b].add(cycles[m*BETS+b]);
            }
            for (auto &p:pairs) p.add(cycles);
            if ((shoe+1)%250000==0) std::cerr<<threshold<<" cards: "<<shoe+1<<" / "<<shoes<<" shoes\n";
        }
        std::cout<<std::setprecision(17)<<"{\"runtime_seconds\":"<<std::chrono::duration<double>(Clock::now()-start).count()<<",\"method_seconds\":[";
        for (int m=0;m<METHODS;m++) {if(m)std::cout<<",";std::cout<<seconds[m];}
        std::cout<<"],\"stats\":[";for(int m=0;m<MODES;m++){if(m)std::cout<<",";stats[m].print();}
        std::cout<<"],\"pairs\":[";
        for (size_t p=0;p<pairs.size();p++) {if(p)std::cout<<",";const auto &v=pairs[p];std::cout<<"["<<v.a<<","<<v.b;
            for (double x:v.cross)std::cout<<","<<x;
            std::cout<<"]";}
        std::cout<<"]}\n";
    } catch (const std::exception &e) {std::cerr<<e.what()<<"\n";return 1;}
}
