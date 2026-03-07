const TOPICS = {
  sw: [
    { label: "Magonjwa ya Mazao", query: "Mahindi yangu yana madoa ya njano. Ni ugonjwa gani?" },
    { label: "Mbolea", query: "Ninahitaji mbolea gani kwa mahindi?" },
    { label: "Msimu wa Kupanda", query: "Ni wakati gani mzuri wa kupanda mahindi Kenya?" },
    { label: "Mifugo", query: "Ng'ombe wangu hawali vizuri. Nifanye nini?" },
    { label: "Kahawa", query: "Jinsi ya kulima kahawa Kenya?" },
    { label: "Chai", query: "Magonjwa ya chai na jinsi ya kuyatibu?" },
  ],
  ki: [
    { label: "Mirimu ya Mimea", query: "Mahindi yakwa marĩ na madoa. Nĩ mũrimũ ûrĩkũ?" },
    { label: "Mbolea", query: "Ndĩhoyaga mbolea ĩrĩkũ ya mahindi?" },
    { label: "Ihinda rĩa Mbeu", query: "Nĩ ihinda rĩrĩkũ rĩega rĩa gũtema mahindi Kenya?" },
    { label: "Nyamũ", query: "Ngombe ciakwa itirĩ kũria wega. Nĩkĩĩ gũikara?" },
    { label: "Kahawa", query: "Nĩatĩa gũtema kahawa Kenya?" },
    { label: "Chai", query: "Mirimu ya chai na ndawa ciao?" },
  ]
};

export default function TopicQuickSelect({ language, onSelect }) {
  const topics = TOPICS[language] || TOPICS["sw"];

  return (
    <div style={{
      display: "flex",
      flexWrap: "wrap",
      gap: 8,
      padding: "12px 0",
    }}>
      {topics.map((topic, i) => (
        <button
          key={i}
          onClick={() => onSelect(topic.query)}
          style={{
            padding: "6px 12px",
            background: "#fff",
            border: "1px solid #2d7a3a",
            borderRadius: 20,
            color: "#2d7a3a",
            cursor: "pointer",
            fontSize: 13,
            fontWeight: 500,
            whiteSpace: "nowrap"
          }}
        >
          {topic.label}
        </button>
      ))}
    </div>
  );
}
