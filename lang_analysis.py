#coding:utf-8
import codecs, operator, re, lxml, os, random
rus = u"йцукенгшщзхъфывэждаплорячсмитьбю"
import rpy2.robjects as robjects


class Language_Definer:
    def __init__(self):
        self.reTags = re.compile(u"(<.*?>|</.*?>|&.*?;|:.*?:|#.*?;)")#|\\[\\[.*?]\\])")
        self.reSpaces = re.compile(u"\\s{2,}")
        self.reNewLine = re.compile(u"(\r|\n)")
        #self.reExtraSymbols = re.compile(u"([0-9#&]|(\\w|^| )[A-Za-z]+?(\\w|$| )|перенаправление|REDIRECT|redirect|mode)")
        self.reExtraSymbols = re.compile(u"([0-9#&]|перенаправление|REDIRECT|redirect|mode|charinsert)")
        self.reUrl = re.compile(u'''((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))''')
        self.reTextStart = re.compile(u"<text.*?>")
        self.reTextEnd = re.compile(u"</text.*?>")
        self.rePunct = re.compile( u"[%s]" % re.escape(u"!?.,…()[]|\/{}-+=;:'"))
        self.wikilimit = 6000000 ##для тестирования выставляется максимальное количество символов текста, который изымается из вики, 0 - если нет лимита
        self.category_profiles = []
        self.current_language = u""
        self.alphabets = self.load_alphabets()
        self.languages = {}
        self.load_languages()

    ##преобразует файл с вики в текстовый файл лишь с нужным текстом
    def wikifile_to_textOLD(self, filename):
        from lxml import etree
        print "make tree of %s " % filename
        tree = etree.parse(filename, etree.HTMLParser(encoding='utf-8'))
        print "tree is ready\nretrieving text from %s..." % filename
        text = u" "
        root = tree.getroot()
        for t in root.iter():
            if len(text) > self.wikilimit and self.wikilimit != 0: return text
            if t.tag == "text" and t.text is not None: # ЗДЕСЬ ПОЛУЧАЕМ ТЕКСТ!!
                print filename, "- ok"
                return
                text += self.delete_special_char(t.text.lower())
        print filename, "- NO TAG TEXT"
        print u"...%s symbols in file named %s..." % (len(text), filename)
        return text

####загрузка списка символов языков
    def load_alphabets(self):
        f = codecs.open(u"alphabet.txt", "r", "utf-8")
        dict = {}
        for line in f:
            reg = re.search(u"\\[(...?)\\](.*)(\r\n|$)", line)
            if reg:
                dict[reg.group(1)] = reg.group(2)
        f.close()
        return dict

    def load_languages(self):
        f = codecs.open(u"languages.csv", "r", "utf-8")
        for line in f:
            key_value = line.strip().split(";")
            self.languages[key_value[1]] = key_value[0]
        f.close()
        return self.languages

    ##преобразует файл с вики в текстовый файл лишь с нужным текстом
    def wikifile_to_text(self, filename):
        lang = re.search(u"xml/(...?)wiki", filename).group(1)
        self.current_language = lang
        print "opening ", filename
        f = codecs.open(filename, "r", "utf-8")
        try:
            f2 = codecs.open("category_texts/" + lang + "_text.txt", 'r', 'utf-8')
            print lang + "_text.txt" + "already exists"
            f2.close()
            return
        except: pass
        fOut = codecs.open("category_texts/" + lang + "_text.txt", 'w', 'utf-8')
        alltext = u""
        print filename, "reading"
        repeats = set()
        textHere = False
        for line in f:
            length = 5000000
            # if "tyvwiki" in filename: length = 527340
            if len(alltext) > length: break
            # if len(alltext) > 911228:
            #     print line
            # print len(alltext)
            # if len(alltext) > 527340: break
            if textHere is False:
                if self.reTextStart.search(line) is not None: textHere = True

            if textHere:
                newLine = self.delete_special_char(line)
                if len(newLine) > 20 and newLine not in repeats:
                    alltext += newLine + "\r\n"
                    repeats.add(newLine)

            if textHere is True:
                if self.reTextEnd.search(line) is not None: textHere = False

        f.close()
        # print len(alltext)
        fOut.write(alltext)
        fOut.close()
        return

#фильтрация токенов строки у которых нет символов текущего языка
    def alphabet_filter(self, string):
        tokens = string.lower().split()
        result = []
        for t in tokens:
            OK = False
            for char in t:
                if char in self.alphabets[self.current_language]:
                    OK = True
                    break
            if OK is True: result.append(t)
        # print string, " ------ original"
        # print u" ".join(result), " ------ processed"
        return u" ".join(result)

    ##принимает на вход строку, возвращает строку без служебных символов: тегов, лишних пробелов, ссылок
    def delete_special_char(self, line):
        line = self.reTags.sub(u"", line)
        #line = self.reUrl.sub(u"", line)
        line = self.reNewLine.sub(u"", line)
        line = self.rePunct.sub(u" ", line)
        line = self.reExtraSymbols.sub(u"", line)
        line = self.reSpaces.sub(u" ", line)
        line = self.alphabet_filter(line)
        return line

    def gram_refine(self, string):
        string = string.strip(u"!?.,…()[]|_\/{}-–+=;:'123456789*%— ")
        string = u" %s " % string
        return string

    ##принимает текст, делает из него частотный словарь ngram
    def n_grams(self, string, n):
        ngrams = {}
        tokens = self.tokenize(string)
        for tok in tokens:
            tok = self.gram_refine(tok)
            for i in range(len(tok)-n):
                gram = u""
                for j in range(n):
                    gram += tok[i+j]
                if gram in [u'', u" ", u"  "]: continue
                if gram in ngrams:
                    ngrams[gram] += 1
                else:
                    ngrams[gram] = 1
        return ngrams

    def tokenize(self, string):
        return string.lower().split()

    ##принимает текст, делает из него частотный словарь ngram(удалить)
    def n_grams_OLD(self, string, n, ngrams = {}):
        string = self.gram_refine(string)
        for i in xrange(len(string)-n):
            gram = u""
            for j in range(n):
                gram += string[i+j]
            if gram in ngrams:
                ngrams[gram] += 1
            else:
                ngrams[gram] = 1
        return ngrams

            # print len(ngrams)

    ##принимает частотный словарь с ngrammами и возвращает отсортированный по убыванию
    ##массив кортежей (нграмма, частотность), напр. (u'th', 15351); берет только первые 300 n-gramm
    def rank(self, ngrams):
        sorted_ngrams = sorted(ngrams.iteritems(), key=operator.itemgetter(1), reverse=True)
        sorted_ngrams = sorted_ngrams[:300]
        # for i in sorted_ngrams:
        #     print u"{%s;%s}" % (i[0],i[1])
        try:
            if len(sorted_ngrams[0][0]) == 1: sorted_ngrams = sorted_ngrams[:45] #если это 1-граммы, то берем только первые 43 символа
        except: pass
        return sorted_ngrams

    def distance_multiplier(self, distMod, multiplier):
        # multiDictionary = {1: }
        # for i in multiDictionary:
        #     if i == multiplier:
        #         distMod -= multiDictionary[i]
        #         return distMod
        distMod = distMod - multiplier*0.5
        return distMod

    #возвращает сумму отклонения document (sorted_ngrams) от category_profile (массива с ngram языка)
    def get_distance_measure(self, document, category):
        distance = 0
        for i in range(len(document)): # document[i] - кортеж типа ('th', 888), [i][0] - ngramma, [i][1] - частотность
            gramTuple = document[i]
            gram = gramTuple[0]
            if gram in category.dictionary:
                catDictTuple = category.dictionary[gram] ## кортеж из ранга nграммы и ее частотности в профиле языка
                distanceModifier = max(catDictTuple[0], i)- min(catDictTuple[0], i) #i является в данном случае рангом нграммы в профиле документа
                distance += self.distance_multiplier(distanceModifier, len(gram))
            else: # если нграмма документа отсутствует в языке для сравнения, добавляется 300-i в отклонение
                distance += (300-i)*(10-len(gram)) ## т.к. это значт что нграмма в профиле языка если и есть то она за пределами этих трехсот "золотых" ngramm
        return distance

    #принимает словарь с языком и дистанцией от текста
    def distance_summary(self, distanceDict):
        minimum = False
        sorted_ngrams = sorted(distanceDict.iteritems(), key=operator.itemgetter(1))
        return sorted_ngrams

    #принимает на вход текст и возвращает
    def compare_by_rank(self, text, text_ind=""):
        if self.category_profiles == []: self.load_categories()
        if text_ind != "": print "text language is %s" % text_ind #для тестирования, если мы знаем какого языка документ, записываем под text_ind
        resultsDists = {} #сюда помещаются ID языка и его дистанция
        for n in range(1,10):
            ngramFreq = self.rank(self.n_grams(text, n))
            # backup = 0
            for category in self.category_profiles:
                if category.n != str(n): continue
                distance = self.get_distance_measure(ngramFreq, category)
                # mindist = min(backup, distance)
                # backup = distance
                if category.language in resultsDists: resultsDists[category.language] += distance
                else: resultsDists[category.language] = distance
        summary = self.distance_summary(resultsDists)
        return summary[0]



    #загрузить в self.category_profiles массив классов профилей языков(категорий)
    def load_categories(self):
        for root, dirs, files in os.walk('category_profiles'):
            for f in files:
                from lxml import etree
                #print "make tree of %s " % f
                tree = etree.parse('category_profiles/' + f, etree.HTMLParser(encoding='utf-8'))
                #print "tree is ready\nretrieving text from %s..." % f
                root = tree.getroot()
                for t in root.iter():
                    if t.tag == "lang": language = t.text
                    if t.tag == "ngrams":
                        category = CategoryProfile()
                        category.language = language
                        category.n = t.attrib['n']
                        grams = t.text.split(u"|")
                        if category.n == "1": grams = grams[:40]
                        for i in range(len(grams)):
                            ngram = grams[i]
                            ngram = ngram.split(u";")
                            category.dictionary[ngram[0]] = (i, ngram[1]) ### ngram[0] - нграмма, i - ранг, ngram[1] - частотность
                        self.category_profiles.append(category)

    ## R SECTION ## not yet used
    def calculate_correlation(self, document, category):
        docAr, catAr = [], []
        for gram in document:
            docAr.append(int(gram[1]))
            if gram[0] in category:
                catAr.append(int(category[gram[0]][1]))
            else: catAr.append(0)
        return self.calculate_r_cor(docAr, catAr) #self.calculate_student_test or calculate_r_cor


    def array_of_num_to_str(self, ar):
        newAr = []
        for i in ar: newAr.append(str(i))
        return newAr

    def calculate_r_cor(self, array1, array2):
        robjects.r('a1 <- c(' + ', '.join(self.array_of_num_to_str(array1)) + ')')
        robjects.r('a2 <- c(' + ', '.join(self.array_of_num_to_str(array2)) + ')')
        robjects.r('c <- cor(a1,a2)')
        cor = str(robjects.r('c'))
        correlation = re.sub(u".*\\[1\\] (.*)", u"\\1", cor)
        try:
            return float(correlation)
        except:
            return -1.0

    def compare_by_correlation(self, text, text_ind=""):
        if self.category_profiles == []: self.load_categories()
        if text_ind != "": print "\r\ntext language is %s" % text_ind #для тестирования, если мы знаем какого языка документ, записываем под text_ind
        resultsCors = {} #сюда помещаются ID языка и его суммированная корреляция

        for n in range(1,5):
            ngramFreq = self.rank(self.n_grams(text, n))
            for category in self.category_profiles:
                if category.n != str(n): continue
                correlation = self.calculate_correlation(ngramFreq, category.dictionary)
                if category.language in resultsCors: resultsCors[category.language] += correlation
                else: resultsCors[category.language] = correlation
        summary = sorted(resultsCors.iteritems(), key=operator.itemgetter(1), reverse=True)
        print summary
        return summary[0]

    ##возвращает название языка по коду
    def get_language_name_by_code(self, code):
        return code

    ##возвращается язык текста
    def get_language(self, text, mode="lang", text_language = ""):
        compare = LD.compare_by_rank(text, text_language)
        if mode == "lang":
            return self.get_language_name_by_code(compare[0])
        else:
            for l in compare: print l
        return compare[0]

    ##главная функция определения языка и вывода результата (выводится только наиболее вероятный)
    def default_definer(self, text):
        return u"Язык текста: " + self.languages[self.compare_by_rank(text)[0]]

#класс профиля категории, то есть собрание ngram языка
class CategoryProfile:
    def __init__(self):
        self.language = u""
        self.n = 2
        self.dictionary = {}


def get_wiki_filenames():
    for root, dirs, files in os.walk('wiki_files\\xml'):
        for i in files:
            yield i

LD = Language_Definer()

# for line in f:
#     line = LA.delete_special_char(line)
#     if len(line) > 4:
#         LA.n_grams(line, 2)
# import sys
# print sys.getsizeof(text)/1024/1024
# exit()

#юзать когда нада (один раз в жизнь желательно)
def make_texts_from_xml():
    LD = Language_Definer()
    for f in get_wiki_filenames():
        # if "cewiki" in f: break
        LD.wikifile_to_text("wiki_files/xml/" + f)
        print f, " - ready"


def make_category_profile_files():
    LD = Language_Definer()
    for root, dirs, files in os.walk('category_texts'):
        for f in files:
            ft = codecs.open('category_texts/' + f, 'r', 'utf-8')
            fCategory_profile = codecs.open('category_profiles/%sprofile.xml' % f[:-8], 'w', 'utf-8')
            fCategory_profile.write(u"<lang>%s</lang>\r\n" % f[:-9])
            fR = ft.read().replace(u"\r\n",u" ")
            ft.close()
            for i in range(1,10):
                ranked = LD.rank(LD.n_grams(fR, i))
                rankedArray = []
                for gr in ranked:
                    rankedArray.append(u";".join([gr[0], str(gr[1])]))
                fCategory_profile.write(u"<ngrams n=\"%s\">%s</ngrams>\r\n" % (str(i), u"|".join(rankedArray)))
            fCategory_profile.close()

###tests sector###
#make_category_profile_files() ###раскоментить если нужно сделать профили снова
#make_texts_from_xml()

# for i in range(2,5):
#     ranked = LD.rank(LD.n_grams("ashdjsahj asjfh jas fyuiyuiywqr usi ya fas hsjfafhk ", i))
#     print ranked[0][0], ranked[0][1]

# exit()
# text = LD.wikifile_to_text("wiki_files/avwiki.xml")

## тестовая функция для проверки заготовленных файлов
def check_documents():
    LD = Language_Definer()
    for root, dirs, files in os.walk('documents'):
        right = 0
        false = []
        all1 = 0
        for f in files:
            docfile = codecs.open('documents/' + f, 'r', 'utf-8')
            document = docfile.read()
            all1 += 1
            compare = LD.compare_by_rank(document, f) #correlation/rank
            if compare[0] == f[:-8]:
                right += 1
            else:
                false.append(u"%s -> %s" % (f[:-8], compare[0]))
                pass #print f[:-8], compare[0]
            docfile.close()
    return "%s/%s is right (%s)" % (right,all1, u";".join(false)), (right, all1)



def heavy_test():
    result = codecs.open('global_test.txt', 'w', 'utf-8')
    aux = u""
    for wordLimit in range(10, 201, 10): #со скольки слов начать, до скольки, по сколько (10, 800, 50)
        result.write(u"----Documents with %s words---\r\n" % wordLimit)
        array, mean = [], 0.0
        for repeats in range(10):
            make_docs(wordLimit)
            check = check_documents()
            result.write(check[0] + u"\r\n")
            array.append(float(check[1][0])/float(check[1][1]))
        print array, "array"
        for i in array:
            mean += i
        mean = mean/len(array)
        aux += u"%s;%s\r\n" % (wordLimit, mean)
    result.close()
    table = codecs.open('global_test_table.csv', 'w', 'utf-8')
    table.write(aux)
    table.close()

def random_line(cat):
    import random
    afile = codecs.open(cat, 'r', 'utf-8')
    line = next(afile)
    for num, aline in enumerate(afile):
      if random.randrange(num + 2): continue
      line = aline
    afile.close()
    return line

# print check_documents()
def make_docs(wordsLimit=300):
    print wordsLimit
    LD = Language_Definer()
    LD.load_categories()
    for prof in LD.category_profiles:
        if prof.n != "2": continue
        caText = 'category_texts/' + prof.language + u"_text.txt"
        catDoc = 'documents/' + prof.language + u"_doc.txt"
        f = codecs.open(caText, 'r', 'utf-8')
        fOut = codecs.open(catDoc, 'w', 'utf-8')
        writeText = u""
        wordsNumber = 0
        lines = f.readlines()
        while wordsNumber < wordsLimit:
            for i in random.choice(lines).strip().split():
                writeText += i + u" "
                wordsNumber += 1
                if wordsNumber < wordsLimit:
                    break
        fOut.write(writeText)
        f.close()
        fOut.close()

def make_docs_v_01(wordsLimit=300):
    LD = Language_Definer()
    LD.load_categories()
    for prof in LD.category_profiles:
        if prof.n != "2": continue
        caText = 'category_texts/' + prof.language + u"_text.txt"
        catDoc = 'documents/' + prof.language + u"_doc.txt"
        f = codecs.open(caText, 'r', 'utf-8')
        fOut = codecs.open(catDoc, 'w', 'utf-8')
        writeText = u""
        wordsNumber = 0
        for line in f:
            if wordsNumber > wordsLimit: break
            line = line.split()
            for i in line:
                for ng in prof.dictionary:
                    if ng in i:
                        writeText += i + u" "
                        wordsNumber += 1
                        break
        fOut.write(writeText)
        f.close()
        fOut.close()

#heavy_test()
#LD.get_language(u"калаçакансем", "array")

#print LD.default_definer(u"мама любит папу. А деревья растут в лесу. Кто же здесь у нас живет?")



